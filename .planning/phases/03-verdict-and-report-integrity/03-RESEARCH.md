# Phase 3: Verdict and Report Integrity - Research

**Researched:** 2026-09-10
**Domain:** Report/verdict aggregation over an existing rule engine (openpyxl workbook building, pandas row-identity counting, Streamlit presentation) — no new QC rules, no new external services.
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Score When a Layer Did Not Run (VERDICT-05)**
- D-01: A layer that ran zero checks earns no credit; weighted contribution is 0; overall score is the plain sum of layers that ran; total is displayed against the achievable maximum — `72.0% of 80.0% achievable` — wherever the weighted score appears (top metric bar, Tab 2 score panel, report cover, email). A bare capped total and renormalising weights were both offered and rejected.
- D-02: Tab 2 score breakdown: a not-run layer shows Layer Pass Rate `n/a` and Weighted Contribution `0` (a number, not `n/a`), weight column unchanged. Total row carries the achievable maximum.
- D-03: Score colour bands stay absolute (green ≥80, amber ≥60, red <60) off the capped score out of 100, never relative to the achievable maximum.
- D-04: When every check that ran passed but a layer did not run, verdict is still CLEAN, with the gap named in the same sentence: `CLEAN — Takeoffpoint layer not checked (no Takeoffpoint data supplied)`. Used identically by the banner, Generate Report tab verdict, report cover, and email verdict line. Two-state only (CLEAN/FAILING); no INCOMPLETE state.
- D-05: "Did not run" = the layer's checks list is empty. Only Takeoffpoint can currently be empty. Implementation must be generic across all five layers.

**Report Workbook Shape (VERDICT-01, VERDICT-02, ENGINE-08)**
- D-06: One combined `QC Summary` sheet plus one detail sheet per layer: Cover · QC Summary · Schema Issue Detail · MLoS Issue Detail · Settlement Issue Detail · Takeoffpoint Issue Detail · Boundary Issue Detail · Raw MLoS Data · Raw Takeoffpoint Data · Columns Renamed (conditional). Summary sheet has a `Layer` column, lists every check in `qc.sort_by_registry` order. Detail frames stay per-layer, not merged. Existing `MLoS QC Summary`/`Takeoffpoint QC Summary` sheet names disappear (costly reversibility). One-summary-per-layer (14 sheets) was offered and rejected.
- D-07: A not-run layer appears as one placeholder row in canonical position on the summary sheet: `Takeoffpoint — not run: no Takeoffpoint data supplied`, with `n/a` in Failing Rows/Total Rows/Fail %.
- D-08: The cover carries the verdict and weighted score only, plus existing file metadata (filename, generated-at, MLoS rows, Takeoffpoint rows). Verdict derived from all five layers — today's `total_fail` (MLoS+TP only) is F1. Per-layer counts live on the summary sheet, not the cover. A per-layer cover table was offered and rejected.
- D-09: Per-cell styling removed from both raw-data sheets AND the five detail sheets: plain values, styled header row, column widths only — no per-cell Font/Border/Alignment/zebra PatternFill. Goes beyond ENGINE-08's literal scope (raw sheets) deliberately, because detail sheets also grow with failures under the free-tier memory constraint. Summary sheet and cover keep their styling (bounded size). Sites: `write_detail`/`write_raw` helpers.

**What One Issue Row Means (VERDICT-04)**
- D-10: Headline Issue Rows figure (top metric c5, failing banner, Generate Report tab, email) is the sum of the per-layer distinct row counts — MLoS, Settlement, Takeoffpoint, Boundary (four layers; Schema excluded). Each layer counts each source row once regardless of how many rules fired on it. A settlement failing in both MLoS and Boundary counts twice in the headline, once per layer. Today every site uses `len(<layer>_detail)` (rule-row pairs) — F8. Two cross-layer distinct figures were offered and rejected; the headline must be exactly the sum of the per-layer lines beneath it.
- D-11: Within a layer, one row = its original row position in the checked frame (index of `mlos_corrected`, or of the Takeoffpoint frame). Every detail frame must carry that position through. MLoS (`qc/mlos.py:268`) and Settlement (`qc/settlement.py:121`) already preserve it (concat without `ignore_index`). Takeoffpoint (`qc/takeoff.py:99`) and Boundary (`qc/boundary.py:188`) pass `ignore_index=True` and must stop discarding it. Keying on `id_col` (`ogc_fid` else first column) was offered and rejected — a CSV without `ogc_fid` may put a non-unique column first.
- D-12: The old rule-row pair count stays visible, labelled as findings, beside the distinct count: `312 issue rows across 1,040 findings`.
- D-13: Each layer's distinct count shown with its share of the checked table's rows: `312 issue rows (6.2% of 5,000) across 1,040 findings`. Denominator is the layer's source table (MLoS row count for MLoS/Settlement/Boundary; Takeoffpoint row count for Takeoffpoint). Schema reports missing-column counts as today; no distinct-row line.

**Email Content (VERDICT-03, VERDICT-04)**
- D-14: Email body restructured as one block per layer, then the check list; stays plain text: D-04 verdict sentence; D-01 weighted score with achievable maximum; five layer blocks in canonical order (checks run, checks failing, D-13 line, or `not run: no Takeoffpoint data supplied`); then check-by-check list grouped under layer headings. Existing Schema missing-columns block stays. Today's body has no Settlement line at all — F11.
- D-15: Check-by-check list includes every check that ran, passing and failing, in canonical order.
- D-16: Subject line carries the verdict: `MLoS QC: FAILING (12 checks) — kano_checkout.xlsx` / `MLoS QC: CLEAN — kano_checkout.xlsx`. Today's static subject is `MLoS QC checks for {filename}`.
- Columns Renamed stays out of the email (Phase 2 D-11's two reporting places stand).

### Claude's Discretion

- Where the verdict/score/counting/report/email-body code lives — must be importable without Streamlit; `tests/test_no_streamlit_in_qc.py`'s boundary must still hold; builders must be unit-testable. `send_qc_email` splits into a pure body-and-subject builder plus a thin secrets-reading sender.
- One derivation, four presentations — banner, cover, Generate Report tab, and email must all read one shared computation (verdict text, weighted score, achievable maximum, per-layer distinct counts, findings counts). Packaging (dataclass/dict/module) is the planner's call; a standing "four sites agree" test is strongly recommended, following the AST-over-`app.py` idiom.
- VERDICT-06 is mostly a proof, not a rebuild — every call site already pipes through `qc.sort_by_registry`. Deliver a standing test asserting order on every summary table and export path; fix any site found not sorted rather than re-sorting inside the boundary layer.
- Generate Report tab layout — whether it becomes five columns, one combined table, or the D-14 layer blocks is the planner's call; must show all five layers and use D-13 counts.
- Whether `of 80.0% achievable` appears in the top metric bar or only in Tab 2 and the cover — `st.metric` has limited room; a delta or caption is acceptable.
- Placeholder-row denominators and `Fail %` for a not-run layer on the summary sheet: `n/a` throughout per D-07; exact cell values are the planner's choice.
- README §8 must be rewritten to match D-01–D-05; §10/§11 should reflect the new sheet list and email shape — required, not optional.
- The longitudinal export (`make_longitudinal_df`, `app.py:167`) is unaffected by D-10–D-13; leave it alone unless a test shows otherwise.
- Baseline and parity tests — preserving the row index in Takeoffpoint/Boundary detail frames (D-11) changes frame shape, not findings; check how `tests/test_extraction_parity.py` and the golden fixture compare indices and adjust deliberately.

### Deferred Ideas (OUT OF SCOPE)

- Email recipients into Space secrets — DEPLOY-03, Phase 4/M2.
- Attaching the Excel report to the email — not in any requirement; backlog note for M2.
- Layer weights and colour-band thresholds in configuration — Phase 6 CONFIG territory.
- HTML email — plain text stays for M1.
- Uniform identifier scheme — deferred at Phase 1 D-05; combined summary's `Layer` column makes the mixed scheme easier to read but does not resolve it.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VERDICT-01 | Report contains summary and detail sheets for all five layers — closes F1 | D-06 sheet list confirmed against `build_excel_report` (`app.py:328-490`); combined `QC Summary` needs `Rule.layer`, which `qc/results.py` does not yet expose (accessor gap identified below) |
| VERDICT-02 | Report cover verdict reads FAILING whenever any layer has a failing check — closes F1 | Root cause confirmed: `total_fail` at `app.py:356-357` sums only `mlos_checks`+`tp_checks`; the fix is to feed the cover the same `all_checks` list the banner/tab8/email already use (`app.py:801-802`) |
| VERDICT-03 | Emailed summary reports Settlement layer counts — closes F11 | `send_qc_email` signature (`app.py:252-254`) confirmed to omit Settlement entirely; must gain settlement counts via D-14's layer-block loop |
| VERDICT-04 | Issue-row totals count distinct rows, not rule-row pairs — closes F8 | Confirmed every row-count site uses `len(<layer>_detail)` (`app.py:806-809`, `1017`, `1055`, `1089`, `1122`, `1229-1230`, `1258-1271`); distinct counting requires D-11's index-preservation fix in `qc/takeoff.py`/`qc/boundary.py` first |
| VERDICT-05 | Weighted score awards no credit for a zero-check layer, shows "n/a" — closes F6 | `_layer_pass_rate` (`app.py:821-825`) returns `1.0` for `not checks`, confirmed live; fix changes return type to `float | None` and the score-summation logic |
| VERDICT-06 | Boundary checks appear B0,B1,B2,B3(,B4,B5) in every summary/export — closes F14 | Confirmed every one of the five QC-layer call sites already pipes through `qc.sort_by_registry` (`app.py:737,747,757,771,781`); this phase is a proof + one new standing test, not a rebuild |
| ENGINE-08 | Raw-data sheets written without per-cell font/border — closes F12 | `write_raw` (`app.py:446-456`) confirmed to assign `Font`/`Border`/`PatternFill` per cell; empirically measured ~12x slower than plain `ws.append()` this session (see Code Examples) |
</phase_requirements>

## Summary

This phase touches no rule logic and adds no dependency — every fact needed is already inside `app.py` and `qc/`, verified by direct reading this session against the exact line numbers 03-CONTEXT.md cites (all matched; 02-04 has already landed on the branch, 02-05/02-06 have not — plan against their `must_haves`, which register `B4`/`B5` and rename `mlos_df`→`mlos_raw`/`mlos_corrected`, not against today's `app.py`). The work is: (1) one shared verdict/score/count computation that today's four independent derivations (banner, cover, Generate Report tab, email) all read instead of recomputing; (2) a report-building module that is importable without Streamlit; (3) a two-line index-preservation fix in `qc/takeoff.py` and `qc/boundary.py` so distinct-row counting is possible at all; (4) a per-cell-styling removal in `write_detail`/`write_raw` that is empirically ~12x cheaper and independently verifiable via `Cell.has_style`.

**Primary recommendation:** Build a single Streamlit-free module — recommend `qc/report.py` — holding (a) a `QcSummary`/`LayerSummary` computation built once from the five layers' checks+details, (b) the D-04 verdict sentence, D-01 score-with-achievable-maximum, and D-10–D-13 distinct/findings counts, and (c) the workbook builder and the email body/subject builder, both reading only that computation. `app.py` calls this once after the five QC layers run (both cache-hit and cache-miss paths) and every presentation site (banner, Tab 2, Tab 8, `build_excel_report`, `send_qc_email`) reads the same object. Placing it under `qc/` means `tests/test_no_streamlit_in_qc.py`'s existing AST scan covers it for free with zero additional guard code.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Verdict/score/count computation | Backend (pure Python, `qc/`) | — | Must be importable and unit-testable without Streamlit (Claude's Discretion note); it is business logic, not UI |
| Excel workbook building | Backend (pure Python, `qc/` or top-level) | — | Same testability requirement; openpyxl has no Streamlit dependency |
| Email body/subject construction | Backend (pure Python) | — | Must be unit-testable; only SMTP transport needs `st.secrets` |
| Email transport (SMTP send) | Frontend Server / orchestration (`app.py`) | — | Reads `st.secrets`, which only exists inside a Streamlit runtime |
| Session-state caching of the computation | Frontend Server (`app.py`, `st.session_state`) | — | `qc/` stays Streamlit-free per ENGINE-05; the cache wrapper is UI-layer orchestration, same split Phase 1 D-08 already established for loaders |
| On-screen presentation (banner, tabs, metrics) | Browser via Streamlit widgets (`app.py`) | — | `st.metric`, `st.markdown`, `st.dataframe` calls, unchanged tier from today |
| Rule identity / canonical order (`Rule.layer`, `sort_by_registry`) | Backend (`qc/results.py`, `qc/__init__.py`) | — | Already established in Phase 1; this phase only needs a new *read* accessor, not new machinery |

## Standard Stack

No new libraries. Every capability this phase needs is already a pinned dependency.

### Core (already pinned — no change)
| Library | Version (pinned) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | `==3.0.5` | DataFrame index-preservation for distinct-row counting, `.nunique()` | Already the project's sole data layer (ENGINE-07) |
| openpyxl | `>=3.1.0,<4.0.0` | Workbook building, `Cell.has_style` for the ENGINE-08 test | Already pinned; verified installed version `3.1.5` in this environment [VERIFIED: `python3 -c "import openpyxl; print(openpyxl.__version__)"` this session] |
| streamlit | `>=1.32.0,<2.0.0` | `st.metric` for score display | Already pinned; `st.metric`'s `delta`/`help` params predate 1.32.0 [CITED: Context7 `/streamlit/docs`, `streamlit.json` API database, signature captured at v1.47.0] |

**Version verification:** `python3 -c "import openpyxl; print(openpyxl.__version__)"` → `3.1.5` [VERIFIED: run this session]. `pip index versions` was not run (no new packages to check); `requirements.txt` upper bounds already satisfy ENGINE-07's pinning requirement for every library this phase touches.

**Installation:** none required — no `pip install` changes for this phase.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `openpyxl` normal-mode workbook with plain-value body cells | `openpyxl.Workbook(write_only=True)` | Write-only mode is ~10MB-memory-bounded and requires `lxml`, but forbids reading back styled ranges or mixing plain writes with the Cover/Summary sheets' existing rich styling in the same `Workbook` object — not worth the split for this phase's sheet count. D-09 already achieves the memory win (no per-cell style objects) without changing write mode. |
| A hand-rolled verdict dataclass | `dataclasses.dataclass` (stdlib) | None — stdlib `dataclass` is the established pattern already in `qc/results.py`'s `Rule`; reuse it for the new `LayerSummary`/`QcSummary` types rather than inventing a dict-of-dicts shape. |

## Package Legitimacy Audit

**Not applicable — no new external packages are installed by this phase.** Every library used (`pandas`, `openpyxl`, `streamlit`) is already pinned in `requirements.txt` with an upper bound (ENGINE-07, closed in Phase 1). No `npm view`/`pip index versions`/`cargo search` run is needed because nothing new is added to the dependency graph.

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```text
Upload (sqlite/csv/xlsx)
        │
        ▼
qc.loaders.load_submission ──► mlos_raw, takeoff_df   (Phase 2's two-frame model)
        │
        ▼
qc.autocorrect.auto_correct_mlos ──► mlos_corrected, correction_log
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Five QC layers (unchanged by this phase, called from app.py) │
│  qc.schema │ qc.mlos │ qc.settlement │ qc.takeoff │ qc.boundary│
│  each returns (checks: list[dict], detail: pd.DataFrame)      │
└─────────────────────────────────────────────────────────────┘
        │  five (checks, detail) pairs, each qc.sort_by_registry-sorted
        ▼
┌─────────────────────────────────────────────────────────────┐
│  NEW: qc/report.py — build_summary(layers) -> QcSummary        │
│    • per-layer: ran?, n_pass, n_fail, distinct_rows (D-11),    │
│      findings (D-12), source_row_count, pass_rate|None (D-05)  │
│    • verdict_text (D-04), weighted_score + achievable_max (D-01)│
│    • headline distinct total (D-10, four layers, Schema excl.) │
└─────────────────────────────────────────────────────────────┘
        │  ONE QcSummary object, cached in st.session_state
        │  alongside the five (checks, detail) pairs
        ├──────────────┬───────────────────┬─────────────────────┐
        ▼              ▼                   ▼                     ▼
  banner (app.py)  Tab 2 / Tab 8      build_excel_report      send_qc_email
  st.markdown       st.metric/         (qc/report.py or        body+subject
                     st.dataframe       app.py, openpyxl)       builder (pure)
                                                                      │
                                                                      ▼
                                                          app.py thin sender
                                                          (st.secrets, smtplib)
```

### Recommended Project Structure

```
qc/
├── results.py       # existing — add get_rule(id) / RULES_BY_ID accessor (see Don't Hand-Roll)
├── report.py         # NEW — Streamlit-free: QcSummary/LayerSummary dataclasses,
│                      #   build_summary(), verdict text, workbook builder,
│                      #   email body/subject builder
└── ... (unchanged layers)

app.py                 # orchestration only: call build_summary() once per QC run,
                        #   cache it in session_state, read it at every presentation site,
                        #   thin send_qc_email() wrapper that reads st.secrets and calls
                        #   qc.report.send via smtplib
```

### Pattern 1: One Shared Computation, Four Readers

**What:** A single `build_summary(layers: dict[str, LayerResult]) -> QcSummary` pure function, called exactly once per QC run (both cache-hit and cache-miss branches of `app.py`'s session-state block), producing one object every presentation site reads.

**When to use:** Whenever more than one UI site must agree on a derived value — this is literally what F1 (cover computing its own verdict) violated.

**Example (recommended shape, following the existing `Rule` dataclass convention in `qc/results.py:17-22`):**
```python
# qc/report.py — Streamlit-free (verified pattern: qc/results.py's @dataclass(frozen=True) Rule)
from dataclasses import dataclass, field

@dataclass(frozen=True)
class LayerSummary:
    name: str                      # "Schema" | "MLoS" | "Settlement" | "Takeoffpoint" | "Boundary"
    checks: list                   # sort_by_registry-sorted check dicts
    detail: "pd.DataFrame"
    weight: float                  # LAYER_WEIGHTS[key], unchanged from app.py:813-819
    source_row_count: int | None   # len(mlos_corrected) or len(takeoff_df); None for Schema (D-13)

    @property
    def ran(self) -> bool:
        return len(self.checks) > 0          # D-05: empty checks list = did not run

    @property
    def n_fail(self) -> int:
        return sum(1 for c in self.checks if "FAIL" in c["Status"])

    @property
    def pass_rate(self) -> float | None:
        if not self.ran:
            return None                       # D-02: n/a, not 1.0 (today's F6 bug)
        return (len(self.checks) - self.n_fail) / len(self.checks)

    @property
    def distinct_issue_rows(self) -> int:
        # D-11: count each ORIGINAL row position once, not each rule-row pair.
        # Requires qc/takeoff.py and qc/boundary.py to stop passing ignore_index=True
        # (qc/mlos.py:268 and qc/settlement.py:121 already preserve the index).
        return 0 if self.detail.empty else self.detail.index.nunique()

    @property
    def findings(self) -> int:
        return len(self.detail)               # D-12: old rule-row-pair count, kept visible
```

### Pattern 2: Rule-Layer Lookup for the Combined Summary Sheet

**What:** D-06's combined `QC Summary` sheet needs a `Layer` column per check row. `qc/results.py` registers `Rule(id, layer, name, description)` but exposes only `register()` and `canonical_order()` — no lookup by id.

**Gap confirmed by direct read this session** [VERIFIED: `qc/results.py:1-55`, read in full — `_REGISTRY: dict[str, Rule] = {}` at line 25 is module-private; only `register()` (line 29) and `canonical_order()` (line 49) are defined; no `get()`/`__getitem__`/public accessor exists]. The planner must add one:

```python
# qc/results.py — small addition, same file, no new module needed
def get_rule(id: str) -> Rule:
    """Look up a registered Rule by its identifier. Raises KeyError naming the id if
    it was never registered — mirrors register()'s own fail-loud convention."""
    if id not in _REGISTRY:
        raise KeyError(f"No rule registered for id {id!r}")
    return _REGISTRY[id]
```
Then the summary-sheet row builder does `qc.results.get_rule(check["Rule#"]).layer` to populate the `Layer` column. This is the only new machinery `qc/results.py` needs for this phase.

### Pattern 3: Excel-Legible Distinct-Row Index Preservation (D-11)

**What:** `qc/takeoff.py:99` and `qc/boundary.py:188` currently do `pd.concat(details, ignore_index=True)`. Drop `ignore_index=True` (matching `qc/mlos.py:268` and `qc/settlement.py:121`, which already omit it).

**Verified safe against the existing test suite** [VERIFIED: `tests/fixtures.py:48-55` `normalize_detail()`, read this session — `detail.to_dict(orient="records")` never includes the DataFrame index as a field, only column values; `tests/test_golden_three_format_parity.py`, read in full this session, compares only `(Failing Rows, Total Rows, Status)` tuples per Rule#, never touches detail frames or their indices at all]. Dropping `ignore_index=True` changes nothing any existing assertion inspects.

```python
# qc/takeoff.py:99 — before
return checks, pd.concat(details, ignore_index=True) if details else pd.DataFrame()
# after
return checks, pd.concat(details) if details else pd.DataFrame()

# qc/boundary.py:188 — before
detail_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
# after
detail_df = pd.concat(details) if details else pd.DataFrame()
```

### Pattern 4: Plain-Value Sheet Writing (ENGINE-08/D-09)

**What:** Replace the per-cell `Font`/`Border`/`Alignment`/zebra-`PatternFill` loop in `write_detail`/`write_raw` (`app.py:419-456`) with a styled header row (kept) plus `ws.append(row.tolist())` for body rows (no style calls at all).

```python
# app.py:446-456 write_raw — before (per-cell styling)
for ri, (_, row) in enumerate(df.iterrows(), 2):
    for ci, v in enumerate(row.values, 1):
        c = ws_r.cell(row=ri, column=ci, value=v)
        c.font=body_font; c.border=bdr; c.alignment=lft
        if ri % 2 == 0: c.fill = lgry_fill

# after (D-09: plain values, header row keeps styling, column widths kept)
hdr_row(ws_r, 1, list(df.columns))         # unchanged — header keeps style
for _, row in df.iterrows():
    ws_r.append(row.tolist())               # no per-cell style call at all
for ci in range(1, len(df.columns)+1):
    ws_r.column_dimensions[get_column_letter(ci)].width = 18   # unchanged
```
Apply the identical change to `write_detail` (`app.py:419-443`), keeping its title row and header row styled but dropping the per-row `Font`/`Border`/zebra-`PatternFill` loop for the body.

### Anti-Patterns to Avoid
- **Recomputing the verdict at each site:** the exact shape of F1. Every one of banner/cover/Tab8/email must read the *same* `QcSummary` object, never re-derive `n_fail`/verdict text locally.
- **Counting distinct rows from a merged/reset-index frame:** Tab 6's Boundary Issues export builds `enriched_detail = boundary_detail.merge(ref_lookup, ...)` (`app.py:1161-1165`). `pandas.merge()` always produces a fresh `RangeIndex` on its result — confirmed by pandas' documented `merge` contract, which has no `left_index`/`right_index` argument passed at that call site (verified by reading `app.py:1148-1166` this session: no `left_index=True`/`right_index=True` kwarg present). **Distinct-row counts must be computed from `boundary_detail` before this merge, never from `enriched_detail`.**
- **Re-sorting inside a QC layer to satisfy VERDICT-06:** Phase 1 deliberately left raw emission order alone (`qc/boundary.py`'s own docstring, lines 13-17, confirms B0-B3 emit in `add()` call order, not registry order) and relies on `qc.sort_by_registry` at the call site. Do not add sorting logic inside `qc/boundary.py` itself.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rule→layer lookup for the summary sheet's `Layer` column | A second `{rule_id: layer}` dict maintained in `app.py` or the new report module | Add one `get_rule(id)` accessor to `qc/results.py` (Pattern 2) | A second lookup table is exactly the "second, diverging view" class of bug INTEG-03/F7 already closed once for column names; one source of truth (`_REGISTRY`) must stay the only one |
| Distinct-row counting | A manual `set()` of some id column, or grouping by `settlement_name`/`master_id` | `detail.index.nunique()` after D-11's index-preservation fix | D-11 explicitly rejected keying on `id_col`/`ogc_fid` because a CSV without it may put a non-unique column first and undercount; the DataFrame's own positional index is the only identity guaranteed unique per source frame |
| Workbook memory reduction | `openpyxl.Workbook(write_only=True)` mode migration for the whole report | Drop per-cell style assignment only (Pattern 4) | Write-only mode forbids later re-reading/re-styling ranges and complicates mixing the Cover/Summary sheets (which keep their styling) with the detail/raw sheets in one `Workbook` object; the measured 12x win (below) comes entirely from not assigning styles per cell, not from write-only mode |

**Key insight:** Every "don't hand-roll" here is really the same principle repeated — Phase 1 and Phase 2 already built the one-source-of-truth pattern (rule registry, absence predicate, column normaliser) that closed F3/F2/F7; this phase's job is to extend that same pattern to verdict/score/count, not invent a parallel one.

## Common Pitfalls

### Pitfall 1: Counting Distinct Rows From a Post-Merge Frame
**What goes wrong:** Computing `boundary_summary.distinct_issue_rows` from Tab 6's `enriched_detail` (after `.merge()` with the boundary reference lookup) silently returns the row *count* correctly but the *identity* is now a fresh `RangeIndex`, so if any later code tries to intersect it with another layer's index (e.g. a future cross-layer dedup), the join is meaningless.
**Why it happens:** `pandas.merge()` always resets the index unless `left_index=True`/`right_index=True` is passed; this call site does not pass either.
**How to avoid:** Compute every layer's `distinct_issue_rows` from the layer's own `detail` DataFrame *before* any UI-only enrichment/merge step, and cache that number in the `LayerSummary`/`QcSummary` object rather than recomputing it later from a display-only derivative.
**Warning signs:** A distinct-row count that changes between the QC Summary tab and the Boundary Issues tab's export caption for the same run.

### Pitfall 2: `_layer_pass_rate`'s `not checks` Branch Silently Returning Wrong Types
**What goes wrong:** Today `_layer_pass_rate` (`app.py:821-825`) returns `1.0` (a `float`) for an empty checks list — F6. The naive fix of returning `None` for "did not run" then breaks every downstream arithmetic site (`* LAYER_WEIGHTS[...] * 100`) with a `TypeError` unless every call site is updated together.
**Why it happens:** The function is called at five call sites (`app.py:827-831`) that all assume a float return.
**How to avoid:** Change `_layer_pass_rate`'s contract explicitly to `float | None` as part of `LayerSummary.pass_rate` (Pattern 1), and compute `weighted_contribution` as a *separate* property that returns `0.0` (never `None`) when `pass_rate is None` — matching D-02's explicit "Weighted Contribution `0`, a number not n/a" requirement. Two properties, two contracts, no silent coercion.
**Warning signs:** A `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'` the first time a Takeoffpoint-less file is run after the naive fix.

### Pitfall 3: FAILING Verdict Sentence Omitting the "Layer Not Run" Gap
**What goes wrong:** D-04 only specifies the exact wording for the **all-checks-passed** case (`CLEAN — Takeoffpoint layer not checked ...`). It is silent on what the sentence should say when a layer both has failing checks *and* a different layer did not run in the same submission. Guessing a combined sentence and shipping it as if D-04 covered it risks contradicting a decision the user has not actually made.
**Why it happens:** D-04's own text scopes itself to "When every check that ran passed but a layer did not run" — the FAILING branch is not addressed.
**How to avoid:** Default to `FAILING — {n_fail} check(s) failing` (no gap clause) for the FAILING branch, matching D-16's compact subject-line precedent (`FAILING (12 checks)`), and surface this as an explicit assumption for user confirmation (see Assumptions Log) rather than silently inventing wording that could ship in filed reports (D-04 flags this reversibility as "costly").
**Warning signs:** None automatic — this is a wording-completeness gap, not a code defect; catch it at plan-check/discuss time, not via a test.

### Pitfall 4: Stale Summary on Cache-Hit Path
**What goes wrong:** `app.py`'s QC block caches per-layer `checks`/`detail` in `st.session_state` (lines 706-799) and skips the whole block on a cache hit. If `build_summary()` is called only inside the `else:` (cache-miss) branch, a rerun after a cache hit renders with a stale or entirely absent `QcSummary`.
**Why it happens:** This is the exact class of bug that produced F4 (Phase 2's ENGINE-03) — a derived value computed only on one of the two session-state branches.
**How to avoid:** Call `build_summary()` unconditionally, once, immediately after the `if/else` cache block resolves both branches to the same five `(checks, detail)` pairs — never inside either branch individually. This mirrors D-15's structural guard pattern (Phase 2) for the two-frame model.
**Warning signs:** Metrics/verdict differing between the very first render of a submission and a subsequent tab-switch rerun of the identical cached submission.

## Code Examples

### Verifying "No Per-Cell Styling" — a Concrete, Runnable Test (ENGINE-08/D-09)

`openpyxl.styles.styleable.StyleableObject.has_style` [VERIFIED: `openpyxl/styles/styleable.py:146-150`, read directly from the installed package this session, version `3.1.5` — matches the project's pinned `openpyxl>=3.1.0,<4.0.0`] returns `False` until any style attribute (`font`/`fill`/`border`/`alignment`/`number_format`/`protection`) has actually been *assigned* to that cell; merely reading a style attribute never creates one (`StyleDescriptor.__get__` returns `False`/a default without touching `_style` when `_style is None`).

**Empirically confirmed this session** [VERIFIED: ran directly against openpyxl 3.1.5 in this environment] that `has_style` survives a full `save()`/`load_workbook()` round-trip:
```python
# Verified output this session:
# header has_style: True   (Font(bold=True) was assigned)
# body cell has_style: False  (no style ever assigned)
```

Recommended test pattern for the planner's Wave 0 gap:
```python
import io
import openpyxl

def test_raw_and_detail_sheets_carry_no_per_cell_styling():
    report_bytes = qc.report.build_workbook(summary)   # or build_excel_report(...)
    wb = openpyxl.load_workbook(io.BytesIO(report_bytes))
    for sheet_name in ("Raw MLoS Data", "MLoS Issue Detail"):
        ws = wb[sheet_name]
        header_row = 1  # or 2, per the sheet's own title-row convention
        body_row = header_row + 1
        assert ws.cell(row=header_row, column=1).has_style is True, \
            f"{sheet_name}: header row should keep styling"
        assert ws.cell(row=body_row, column=1).has_style is False, \
            f"{sheet_name}: body cells must carry NO per-cell style (ENGINE-08/D-09)"
```

### Performance: Per-Cell Styling vs. Plain `ws.append()` (ENGINE-08/D-09)

**Empirically measured this session** [VERIFIED: ran directly against openpyxl 3.1.5 in this environment, 3,000 rows × 12 columns = 36,000 cells]:

| Approach | Time | Notes |
|----------|------|-------|
| Per-cell `cell.font=`/`cell.border=`/conditional `cell.fill=` (today's `write_raw`/`write_detail` shape) | 0.420s | Every style assignment triggers `StyleDescriptor.__set__`, lazily allocating a `StyleArray` on first touch and mutating it per attribute per cell |
| `ws.append(row_values)`, no style calls | 0.034s | **12.2x faster** for the same cell count |

Confirmed mechanistically by reading `openpyxl/worksheet/worksheet.py` [VERIFIED: `worksheet.py:641-681` (`append`) and `:220-262` (`cell`/`_get_cell`), read this session]: `append()` and `cell()` do near-identical per-cell `Cell(...)` construction and dict insertion — `append()` skips `cell()`'s bounds-check and dict-membership branches, a minor win. **The 12x measured speedup is overwhelmingly attributable to skipping style assignment, not to `append()` vs `cell()` alone** — a per-cell loop using `ws.cell()` but *without* any `cell.font=`/`cell.border=`/`cell.fill=` calls would capture nearly all of the same win. Recommend `ws.append()` regardless, since it is simpler and matches the existing `build_corrected_excel` precedent (`app.py:310-324`), which already writes plain rows via `df.to_excel(writer, ...)` (pandas' own bulk writer, which internally uses per-cell `ws.cell()` with no post-hoc style assignment beyond the header).

### `qc.sort_by_registry` — VERDICT-06's Existing Mechanism

```python
# qc/__init__.py:26-33 — already exists, no change needed
def sort_by_registry(checks: list[dict]) -> list[dict]:
    order_index = {rule_id: i for i, rule_id in enumerate(canonical_order())}
    return sorted(checks, key=lambda c: order_index[c["Rule#"]])
```
[VERIFIED: `qc/__init__.py:26-33`, read this session] — `sorted()` is stable, and every one of the five QC-layer call sites in `app.py` (lines 737, 747, 757, 771, 781, confirmed by direct read) already pipes its layer's checks through this function before storing them in `st.session_state`. **VERDICT-06's implementation work is a standing test proving every summary table and export reads the already-sorted list, plus fixing any site (if found) that reads the unsorted raw list instead** — for example, Tab 8's three-column breakdown at `app.py:1280-1299` builds its tables directly from `mlos_checks`/`settlement_checks`/`tp_checks`, which are the already-sorted session-state values, so this site is correct today; the per-rule Excel exports in Tabs 4/5/6 (`app.py:1074-1078`, `1107-1111`, `1175-1179`) iterate `for check in <layer>_checks:` over the same sorted lists — also correct today. No unsorted read site was found during this research; the planner should still write the standing test rather than assume this holds forever.

## State of the Art

Not applicable in the "library evolved" sense — this phase works entirely within already-pinned, already-current library versions. The one relevant "old approach → current approach" shift is internal to this codebase, not the ecosystem:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Four independent verdict/count derivations (banner, cover, Tab 8, email), one of which (cover) is wrong | One shared `QcSummary` computation, four readers | This phase | Closes F1 structurally — a future fifth presentation site cannot reintroduce the bug by construction, since it has nothing to compute independently |
| `pd.concat(details, ignore_index=True)` in Takeoffpoint/Boundary | `pd.concat(details)` (index preserved) | This phase (D-11) | Enables distinct-row counting; verified safe against every existing parity/golden test this session |

**Deprecated/outdated:** the `MLoS QC Summary`/`Takeoffpoint QC Summary` per-layer sheet names (D-06 removes them in favour of one combined `QC Summary` sheet) — flagged in CONTEXT.md as a costly, one-way reversibility if anything downstream depends on those exact sheet names.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The FAILING verdict sentence omits the "layer not run" gap clause (`FAILING — {n} check(s) failing`, no mention of an unrun layer even if one exists alongside a failure elsewhere) | Common Pitfalls, Pitfall 3 | If the user actually wants the gap named in the FAILING case too, the planner ships a two-branch sentence template instead of Pitfall 3's simpler default — low code risk, but D-04 flags verdict wording as "costly" reversibility (printed in filed/emailed reports), so confirm before, not after |
| A2 | `st.metric`'s `help=` parameter (not `delta=`) is the right mechanism for surfacing "of 80.0% achievable" in the top metric bar, since `delta` visually implies a change-from-previous value rather than a static ceiling | Standard Stack / Code Examples note (implicit — see Claude's Discretion write-up) | If the planner instead uses `delta` with `delta_color="off"`, the number still displays but with slightly different visual treatment (smaller font, no colored arrow) — cosmetic risk only, both are valid Streamlit API |
| A3 | Recommending `qc/report.py` (under `qc/`) rather than a top-level `report.py` for the new module, on the grounds that it gets `tests/test_no_streamlit_in_qc.py`'s existing AST scan "for free" | Architecture Patterns, Recommended Project Structure | If the planner instead places it at top-level `report.py`, nothing breaks — CONTEXT.md explicitly leaves this as the planner's call — but the module then needs either its own new streamlit-import guard test or an explicit decision that none is needed, since the existing guard (`QC_DIR = repo_root/qc`, `test_no_streamlit_in_qc.py:14`) would not scan it |

**If this table is empty:** N/A — three assumptions recorded above; none are load-bearing blockers, all are cheap to confirm at discuss/plan-check time.

## Open Questions

1. **Does the FAILING verdict sentence need a "layer not run" gap clause when a different layer is also failing?**
   - What we know: D-04 gives the exact CLEAN-with-gap wording and states the verdict stays two-state; D-16 gives a compact FAILING subject-line format (`FAILING (12 checks)`).
   - What's unclear: whether the FAILING *body* sentence (banner/cover/Tab8/email body, not the email subject) should also name an unrun layer when one exists.
   - Recommendation: default to Pitfall 3's plain `FAILING — {n} check(s) failing` (no gap clause) and flag it as A1 in the Assumptions Log for confirmation, rather than blocking planning on it — the plan can be written either way with a one-line difference in the verdict-sentence builder.

2. **Should the not-run placeholder row's `Fail %` column literally contain the string `"n/a"`, or should the column be blank/empty for that row?**
   - What we know: D-07 says "`n/a` in Failing Rows, Total Rows and Fail %" — this reads as settled, not actually open.
   - What's unclear: nothing substantive; listed only because the existing `write_summary` helper (`app.py:398-416`) writes `row[key]` directly into the cell for every column, so the check dict for a placeholder row must literally carry the string `"n/a"` in those three keys (not `None`/`NaN`, which would render as a blank Excel cell instead of the word "n/a").
   - Recommendation: build the placeholder check dict with `"Failing Rows": "n/a", "Total Rows": "n/a", "Fail %": "n/a"` (all strings) so it flows through the existing `write_summary` helper unchanged.

## Environment Availability

Not applicable — this phase has no external service or tool dependency beyond the already-pinned, already-installed Python libraries (`pandas`, `openpyxl`, `streamlit`), all verified present in this environment this session (`openpyxl.__version__` → `3.1.5`; `requirements.txt` confirms the other two pins). No network access, no database, no new CLI tool.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed via `requirements.txt`'s implicit dev tooling; `pytest.ini` present at repo root) |
| Config file | `pytest.ini` — `testpaths = tests`, `python_files = test_*.py` [VERIFIED: read this session] |
| Quick run command | `python3 -m pytest tests/test_<new_file>.py -q` |
| Full suite command | `python3 -m pytest tests/ -q` — **91 passed** confirmed as the pre-Phase-3 baseline [VERIFIED: ran this session] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VERDICT-01 | Report has summary+detail sheets for all five layers | unit (openpyxl round-trip, no Streamlit) | `pytest tests/test_report_workbook_shape.py -x` | ❌ Wave 0 |
| VERDICT-02 | Cover verdict reads FAILING when any layer fails | unit | `pytest tests/test_verdict_agreement.py -x` | ❌ Wave 0 |
| VERDICT-03 | Email reports Settlement counts | unit (test the pure body-builder function, not SMTP) | `pytest tests/test_email_body.py -x` | ❌ Wave 0 |
| VERDICT-04 | Issue-row totals are distinct-row, not rule-row-pair, counts | unit | `pytest tests/test_distinct_row_counting.py -x` | ❌ Wave 0 |
| VERDICT-05 | Zero-check layer earns no credit, shows n/a | unit | `pytest tests/test_layer_pass_rate.py -x` | ❌ Wave 0 |
| VERDICT-06 | Boundary/all layers in canonical order everywhere | unit (extends existing) | `pytest tests/test_deterministic_order.py tests/test_summary_sheet_order.py -q` | Partial — `test_deterministic_order.py` exists; new summary-sheet-specific test is Wave 0 |
| ENGINE-08 | Raw sheets written without per-cell styling | unit (openpyxl `has_style` check) | `pytest tests/test_no_per_cell_styling.py -x` | ❌ Wave 0 |
| D-11 (index preservation) | Takeoffpoint/Boundary detail frames preserve original row index | unit | `pytest tests/test_extraction_parity.py tests/test_golden_three_format_parity.py -q` (must still pass unmodified per this research's verification) | Exists — extend, don't replace |
| "Four sites agree" (Claude's Discretion, strongly recommended) | Banner/cover/Tab8/email all read one `QcSummary` | unit (AST-over-`app.py`, following `tests/test_no_streamlit_in_qc.py`'s idiom) | `pytest tests/test_one_verdict_computation.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the specific new test file(s) for that task, `-q`
- **Per wave merge:** `python3 -m pytest tests/ -q` (full suite, currently 91 passed baseline — expect this number to grow with each new Wave 0 test file)
- **Phase gate:** full suite green before `/gsd-verify-work`, plus `python3 -m compileall -q qc app.py tests` (the project's configured `build_command`)

### Wave 0 Gaps
- [ ] `tests/test_report_workbook_shape.py` — covers VERDICT-01 (sheet list, `Layer` column present via `qc.results.get_rule`)
- [ ] `tests/test_verdict_agreement.py` — covers VERDICT-02, and doubles as the "four sites agree" structural proof via AST if the planner combines it with the Discretion recommendation
- [ ] `tests/test_email_body.py` — covers VERDICT-03/VERDICT-04/D-14/D-15/D-16, testing the pure body/subject builder (no SMTP mock needed since the builder takes no `st.secrets`)
- [ ] `tests/test_distinct_row_counting.py` — covers VERDICT-04/D-10/D-11/D-12/D-13, using a fixture where one settlement fails in two layers (proves the "counts twice in the headline, once per layer" rule)
- [ ] `tests/test_layer_pass_rate.py` — covers VERDICT-05/D-01/D-02/D-05, including the zero-checks-returns-None-not-1.0 regression case for F6
- [ ] `tests/test_no_per_cell_styling.py` — covers ENGINE-08/D-09, using the `has_style` pattern verified in Code Examples above
- [ ] `tests/test_summary_sheet_order.py` — covers VERDICT-06 specifically for the new combined summary sheet's row order (extends, does not duplicate, `tests/test_deterministic_order.py`'s cross-process determinism proof)
- [ ] Framework install: none — pytest and openpyxl are already present and pinned

**Recommended shared fixture** (per the Research focus's own suggestion, confirmed workable): a fixture MLoS/Takeoffpoint pair where Boundary has at least one failing check and the Takeoffpoint table is empty exercises D-01 (no-credit scoring), D-04 (CLEAN-with-gap or FAILING-with-gap wording), D-07 (placeholder row), and F1 (cover must show the Boundary failure) all in one fixture — reuse `tests/fixtures.py`'s existing `build_mlos_fixture()` (which already has a Boundary-failing row, per its own docstring) paired with `pd.DataFrame()` for the Takeoffpoint side, mirroring the existing `test_takeoff_layer_returns_nothing_for_an_empty_frame` pattern [VERIFIED: `tests/fixtures.py` docstring and `tests/test_extraction_parity.py:345-351`, both read this session].

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Deferred to Phase 4 (AUTH-01/02/03); out of this phase's scope |
| V3 Session Management | No (indirectly touched, not changed) | `st.session_state` caching pattern is unchanged in kind by this phase — only the *value* cached (a new `QcSummary` object) is new, not the caching mechanism itself |
| V4 Access Control | No | No access-control surface in this phase |
| V5 Input Validation | Partial — pre-existing, not introduced by this phase | Officer-supplied cell values (settlement names, editor strings, etc.) are written into Excel cells by `write_raw`/`write_detail` without sanitizing leading `=`/`+`/`-`/`@` characters, which some spreadsheet applications interpret as formulas on open (CSV/Excel formula injection). **This risk pre-dates this phase** — `write_raw` already writes raw values today — and ENGINE-08/D-09 only removes per-cell *styling*, not value handling, so this phase does not introduce or worsen the exposure. Flagged for awareness, not remediation, since no phase requirement (VERDICT-01–06, ENGINE-08) asks for input sanitization and CONTEXT.md does not mention it. |
| V6 Cryptography | No | No cryptographic operation in this phase (sha256 content-identity is Phase 2's D-13, unchanged here) |

### Known Threat Patterns for This Phase's Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSV/Excel formula injection via officer-supplied cell values (settlement names, editor field, etc.) written unsanitized into `.xlsx` cells | Tampering (client-side, in the officer's own spreadsheet application on open) | Prefix any string cell value beginning with `=`, `+`, `-`, or `@` with a leading single-quote/apostrophe before writing (industry-standard Excel/CSV injection mitigation) — **not requested by any Phase 3 requirement or CONTEXT.md decision; recorded here as a candidate follow-up, not a blocking finding for this phase's plan** |
| Report/email describing a different verdict than what actually ran (the class of bug this whole phase exists to close) | Repudiation / Tampering (a false "CLEAN" is a trust violation, not a memory-safety one) | The One Shared Computation pattern (Pattern 1) — this **is** the phase's actual security-relevant work, in the sense that Core Value ("a file this tool calls clean is clean") is a data-integrity guarantee, not a conventional CWE-class vulnerability |

## Sources

### Primary (HIGH confidence)
- `app.py` (this repository, read in full this session, lines 1-1344) — every verdict/score/count/report/email site cited above, confirmed against 03-CONTEXT.md's line-number citations (all matched)
- `qc/results.py`, `qc/__init__.py`, `qc/mlos.py`, `qc/settlement.py`, `qc/takeoff.py`, `qc/boundary.py`, `qc/schema.py`, `qc/predicates.py` (this repository, each read in full this session)
- `tests/test_no_streamlit_in_qc.py`, `tests/test_deterministic_order.py`, `tests/test_registry_covers_emitted_ids.py`, `tests/test_extraction_parity.py`, `tests/fixtures.py`, `tests/conftest.py`, `tests/test_golden_three_format_parity.py`, `tests/test_rules_reference_matches_registry.py` (this repository, each read in full or substantially this session)
- `openpyxl/styles/styleable.py`, `openpyxl/worksheet/worksheet.py` (installed package source, version 3.1.5, read directly this session at `/System/Volumes/Data/opt/homebrew/lib/python3.13/site-packages/openpyxl/`)
- Empirical benchmark and `has_style` round-trip test, run directly in this session against openpyxl 3.1.5

### Secondary (MEDIUM confidence)
- Context7 `/websites/openpyxl_readthedocs_io_en_stable` — styles.html, optimized.html, performance.html pages (styles-are-shared-and-immutable, write-only-mode memory bound, "~50x file size" memory rule of thumb)
- Context7 `/streamlit/docs` — `streamlit.json` API signature database, `st.metric` signature captured at v1.47.0 (project pins `>=1.32.0,<2.0.0`; `delta`/`help` params confirmed present well before 1.32 via the `label_visibility` 2022/v1.16.0 release note, which implies `delta`/`help` already existed at that earlier version)

### Tertiary (LOW confidence)
- None — every claim above is either read directly from this repository's source this session, read directly from the installed dependency's source this session, empirically measured this session, or cited from official documentation via Context7.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every version claim verified against the installed environment or `requirements.txt` directly
- Architecture: HIGH — every code site cited was read in full this session; the one new pattern (`get_rule` accessor) is a two-line addition following an existing dataclass convention already in the codebase
- Pitfalls: HIGH — each pitfall is either a confirmed code fact (e.g. `merge()` resetting the index, absence of `left_index=True`) or an explicit scoping gap in CONTEXT.md's own D-04 text, not a speculative concern

**Research date:** 2026-09-10
**Valid until:** No expiry driven by library drift (no new dependencies); re-verify only if 02-05-PLAN.md/02-06-PLAN.md execute with different line numbers or column-naming than their current `must_haves` describe, since this phase's plans should target their post-execution state, not today's `app.py`.
