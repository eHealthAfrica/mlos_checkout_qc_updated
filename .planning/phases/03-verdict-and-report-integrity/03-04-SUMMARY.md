---
phase: 03-verdict-and-report-integrity
plan: 04
subsystem: qc-engine
tags: [ordering, ast-guard, standing-test, verdict-agreement, readme, streamlit-free]

requires:
  - phase: 03-verdict-and-report-integrity
    provides: "qc/report.py's QcSummary/LayerSummary/build_summary() (plan 01),
      summary_rows()/build_workbook() (plan 02), build_email_subject_and_body() (plan 03) --
      the four presentation-site readers and the registry re-sort this plan proves order and
      agreement over, rather than building"
provides:
  - "tests/test_summary_sheet_order.py: standing, registry-sourced proof that boundary/rule
    order holds at all four ordered outputs (summary object, summary_rows(), the workbook's
    QC Summary sheet, the emailed check list), across three process restarts with differing
    PYTHONHASHSEED values (VERDICT-06, closes F14)"
  - "tests/test_verdict_agreement.py: standing proof that the verdict sentence, score string
    and headline issue-row figure are character-identical at the workbook cover, the email
    body and (structurally) the banner and Generate Report tab; and that every registry layer
    appears at every presentation site (the assumption-delta companion invariant)"
  - "qc.report.count_failing(checks) and qc.report.LAYER_LABELS -- the shared per-layer
    fail-count and display-label helpers app.py's progress narration and score table now read
    instead of recomputing/naming layers locally"
  - "README.md sections 8, 10 and 11 rewritten to match this phase's shipped scoring, report
    and email behaviour"
affects: []

actuals:
  tokens: 11861
  tasks: 3
  commits: 3
  plan_head_before: 26e7700f112dedde80320b52c514250668cdcd4a

tech-stack:
  added: []
  patterns:
    - "Order proofs read qc.canonical_order() at test time, never a literal identifier list --
      a rule registered by a future phase extends the assertion instead of falling outside it"
    - "AST offender-set scans over app.py (parsed, not imported, since it needs a Streamlit
      runtime): collect offenders into a list, assert empty, separately assert a non-zero
      count of examined nodes so a mis-resolved parse cannot green the test"
    - "Layer-keyed lookup tables (display labels, not-run reasons, weights) live in
      qc/report.py next to LAYER_ORDER, never as a local app.py dict literal -- so a
      construction site that needs a per-layer value looks it up rather than naming the five
      layers as dict keys itself"

key-files:
  created:
    - tests/test_summary_sheet_order.py
    - tests/test_verdict_agreement.py
  modified:
    - qc/report.py
    - qc/domain.py
    - app.py
    - README.md

key-decisions:
  - "qc/domain.py's docstring mentioned the literal string \"sort_by_registry\" in prose (not
    code); Task 1's own literal verify command is a substring scan over qc/*.py and flagged it
    as a false-positive offender. Reworded the docstring sentence to describe the helper
    without repeating its call-shaped name -- no executable change."
  - "app.py's five per-layer progress-narration lines (printed live as each QC step completes,
    before the shared QcSummary exists) each recomputed sum(1 for c in checks if \"FAIL\" in
    c[\"Status\"]) locally -- the same local-recomputation shape F1/F6/F8 all took, and
    something Task 2's own literal AST offender-set test would (correctly) flag. Added
    qc.report.count_failing() as the one shared implementation and routed
    LayerSummary.n_fail/QcSummary.n_fail through it too, rather than leaving two
    implementations of the same one-line test."
  - "Tab 2's score table looked up each layer's emoji+label from a local app.py dict literal
    keyed on all five layer names -- exactly the \"per-layer name literal used as a dictionary
    key at a presentation construction site\" Task 2's companion-invariant test targets, and
    would raise KeyError (not silently omit) for a future sixth layer. Relocated to
    qc.report.LAYER_LABELS, alongside LAYER_ORDER/LAYER_WEIGHTS/NOT_RUN_REASON, which already
    live in qc/report.py for exactly this reason."

patterns-established:
  - "Registry-sourced expected order in every ordering test: qc.canonical_order() filtered to
    the identifiers that ran for a given fixture, never a hand-written identifier list."

requirements-completed: [VERDICT-06]

coverage:
  - id: D1
    description: "Standing proof (tests/test_summary_sheet_order.py) that boundary check order
      -- and rule order generally -- holds at all four ordered outputs an officer can read: the
      summary object, the combined summary sheet, the downloaded workbook, and the emailed
      check list. Proven for both a full five-layer run and a run with an unrun layer, plus a
      same-process stability/empty-input pair and a three-hash-seed cross-process byte-identical
      proof."
    requirement: "VERDICT-06"
    verification:
      - kind: unit
        ref: "tests/test_summary_sheet_order.py (10 tests)"
        status: pass
      - kind: integration
        ref: "tests/test_deterministic_order.py, tests/test_registry_covers_emitted_ids.py
          (unmodified, still green alongside the new file)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Structural half: the five sort_by_registry call sites in app.py pass exactly
      the five per-layer checks names (one call site per layer); no QC layer module other than
      the report aggregation module references sort_by_registry."
    requirement: "VERDICT-06"
    verification:
      - kind: unit
        ref: "tests/test_summary_sheet_order.py::test_call_sites_pass_exactly_the_five_per_layer_checks_names,
          ::test_no_qc_layer_module_sorts_internally"
        status: pass
    human_judgment: false
  - id: D3
    description: "Standing proof (tests/test_verdict_agreement.py) that the verdict sentence,
      the weighted score string and the headline issue-row figure are character-identical at
      the workbook cover and the email body for a summary whose only failing checks are
      Boundary checks and whose Takeoffpoint layer did not run -- the exact shape F1 reported
      as CLEAN. The two on-screen sites (banner, Generate Report tab) are asserted
      structurally, since app.py cannot be imported outside a Streamlit runtime."
    verification:
      - kind: unit
        ref: "tests/test_verdict_agreement.py::test_verdict_sentence_appears_verbatim_in_the_workbook_cover_and_the_email_body,
          ::test_score_display_appears_verbatim_in_the_workbook_cover_and_the_email_body,
          ::test_headline_issue_line_appears_verbatim_in_the_email_body,
          ::test_verdict_text_is_read_at_the_banner_and_the_generate_report_tab,
          ::test_score_display_is_read_where_the_score_is_rendered"
        status: pass
    human_judgment: false
  - id: D4
    description: "The assumption-delta companion invariant: every layer name the registry knows
      equals qc.report.LAYER_ORDER as a set; every registry layer appears in the combined
      summary sheet's Layer column and in the email body; the Tab 2 score table and Tab 8
      metadata card/breakdown are built by iterating LAYER_ORDER, never by naming 2+ layers as
      dict keys at the construction site (an offender-set AST scan over the tab2/tab8 With
      blocks, asserting a non-zero scanned-block count)."
    verification:
      - kind: unit
        ref: "tests/test_verdict_agreement.py::test_registry_layer_names_equal_report_layer_order,
          ::test_every_registry_layer_appears_in_the_summary_sheet_and_the_email_body,
          ::test_score_table_metadata_card_and_breakdown_iterate_layer_order_not_named_dict_keys"
        status: pass
    human_judgment: false
  - id: D5
    description: "No call in app.py sums over a check-status membership test, and no name in
      app.py is assigned len(<name>_detail) -- an offender-set AST scan, with a non-zero
      examined-Call-nodes floor so a mis-resolved parse cannot green the test."
    requirement: "VERDICT-06"
    verification:
      - kind: unit
        ref: "tests/test_verdict_agreement.py::test_no_offender_recomputes_a_failing_count_or_a_detail_frame_length"
        status: pass
    human_judgment: false
  - id: D6
    description: "README.md §8 describes the score exactly as D-01 to D-05 define it (no-credit
      unrun layer, achievable maximum, n/a breakdown row with numeric 0 contribution, absolute
      colour bands, two-state verdict with the gap clause after either state) with no remaining
      claim that a skipped layer scores as though it passed. §10 lists the real ten-sheet
      workbook order and the D-07 placeholder wording. §11 gives the real D-16 subject template
      (both approved subjects quoted) and the D-14 body structure. §2, §3 and §7 -- including
      the required-columns tables two standing tests parse -- are untouched."
    requirement: "VERDICT-06"
    verification:
      - kind: unit
        ref: "python3 -c '...' README string-presence/absence check (plan <verify>); tests/test_readme_columns_match_domain.py,
          tests/test_rules_reference_matches_registry.py (5 tests, unmodified, still green)"
        status: pass
      - kind: other
        ref: "git diff --stat README.md scoped to exactly §8/§10/§11's line ranges"
        status: pass
    human_judgment: true
    rationale: "The README prose itself (readability, tone, whether the rewritten sections read
      well to an officer) is a judgment call no automated string check can make; the literal
      strings and absence-of-stale-claims are proven, but a human should skim the rendered
      Markdown before this phase ships."

duration: 55min
completed: 2026-09-10
status: complete
---

# Phase 3 Plan 4: Standing Verdict-Order and Verdict-Agreement Proofs, README Rewrite Summary

**Two new standing tests turn this phase's two structural guarantees — canonical rule order at
every export, and one verdict/score/count computation read by all four presentation sites — into
tests that fail the moment a future phase reintroduces the divergence, plus a README rewrite that
brings the manual into line with the shipped scoring, report and email behaviour.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-10T21:05:00Z (approx.)
- **Completed:** 2026-09-10T22:00:00Z (approx.)
- **Tasks:** 3 (Task 1 `type="tracer"`, Tasks 2-3 `type="auto"`; not TDD — plan frontmatter
  carries no `tdd="true"` tasks)
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- `tests/test_summary_sheet_order.py`: proves canonical order (VERDICT-06/F14) at all four
  ordered outputs — the `QcSummary.all_checks` property, `qc.report.summary_rows()`, the
  downloaded workbook's `QC Summary` sheet (read back via an openpyxl round trip), and the
  emailed check-by-check list — for a full five-layer run and a run with an unrun layer, plus a
  stability case (two checks sharing one identifier keep relative order), an empty-input case,
  and a three-`PYTHONHASHSEED` cross-process byte-identical proof reusing
  `tests/test_deterministic_order.py`'s subprocess idiom. Every expected order is read from
  `qc.canonical_order()` at test time — the file contains no hard-coded identifier list.
  Structurally: the five `qc.sort_by_registry(...)` call sites in `app.py` pass exactly the five
  per-layer checks names, and no QC layer module (other than the report aggregation module)
  references `sort_by_registry` internally.
- **RESEARCH.md's own prediction held**: no unsorted read site was found. `app.py`'s call sites
  were already correct; the only fix Task 1 needed was a false-positive docstring match (see
  Deviations).
- `tests/test_verdict_agreement.py`: proves the verdict sentence, the weighted score string and
  the headline issue-row figure are character-identical at the workbook cover and the email body
  for a summary whose only failing checks belong to the Boundary layer and whose Takeoffpoint
  layer did not run — the exact shape F1 used to report as `CLEAN`. The banner and Generate
  Report tab verdict sites are asserted structurally (source-region scans keyed on stable
  comment markers, not line numbers, since app.py cannot be imported outside a Streamlit
  runtime). A second test proves the assumption-delta companion invariant: every layer name the
  registry knows equals `qc.report.LAYER_ORDER` as a set, appears in the combined summary
  sheet's `Layer` column and the email body, and is read by iterating `LAYER_ORDER` — never by
  naming 2+ layers as dict keys — at the Tab 2 score table and Tab 8 metadata card/breakdown.
- **Task 2's own offender-set test found two real violations**, fixed before committing (see
  Deviations): app.py's five progress-narration lines recomputing a failing count locally, and
  the score table's layer-label lookup naming all five layers as dict keys.
- `README.md` §8 "Weighted QC Score", §10 "Generate & Download Report" and §11 "Send QC Email"
  rewritten to describe D-01 through D-16's shipped behaviour — the achievable-maximum score
  display, the `n/a`/numeric-`0` breakdown row, absolute colour bands, the two-state verdict with
  the gap clause, the real ten-sheet workbook order, and the verdict-bearing email subject and
  per-layer-block body. No remaining claim that a skipped layer scores as though it passed.

## Task Commits

1. **Task 1: Standing proof of canonical order at every summary table and export** —
   `ff529be` test(03-04)
2. **Task 2: The four sites agree, and every layer appears at every site** —
   `18212d7` feat(03-04)
3. **Task 3: Rewrite README §8, §10 and §11 to the shipped behaviour** —
   `3d020fd` docs(03-04)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

Not a TDD plan — no `refactor(03-04):` commits, no RED/GREEN cycle; `test`/`feat`/`docs` commit
types per task type, matching the plan's own frontmatter (no `tdd="true"` tasks).

## Files Created/Modified

- `tests/test_summary_sheet_order.py` — new, 10 tests (order-matches-registry at all four
  outputs × 2 scenarios, unrun-layer placeholder/no-check-lines, empty/stability unit cases,
  cross-process hash-seed proof, two structural call-site checks)
- `tests/test_verdict_agreement.py` — new, 9 tests (verdict/score/headline verbatim-in-real-output,
  banner/Generate-Report structural reads, offender-set scan, registry-layer-set equality,
  every-layer-appears, construction-site dict-key scan)
- `qc/report.py` — `LAYER_LABELS` constant and `count_failing(checks)` helper added;
  `LayerSummary.n_fail`/`QcSummary.n_fail` routed through `count_failing` (one implementation,
  not two)
- `qc/domain.py` — one docstring sentence reworded (no executable change)
- `app.py` — five progress-narration lines call `qc.report.count_failing(...)` instead of a
  local `sum(...)`; the Tab 2 score table reads `qc.report.LAYER_LABELS[_name]` instead of a
  local `_LAYER_LABELS` dict literal
- `README.md` — §8, §10, §11 rewritten; §2, §3, §7 untouched

## Decisions Made

- Followed the plan's own literal `<verify>` commands over a looser reading of "no site sorts
  internally" — `qc/domain.py`'s docstring mention of the bare word "sort_by_registry" is not a
  call, but the plan's verify script is a plain substring scan and would fail on it; reworded
  the sentence rather than weaken the check.
- Relocated the per-layer display-label dict (`LAYER_LABELS`) into `qc/report.py` alongside
  `LAYER_ORDER`/`LAYER_WEIGHTS`/`NOT_RUN_REASON`, rather than leaving it as a local `app.py`
  dict literal — consistent with where every other layer-keyed lookup in this phase already
  lives, and required by Task 2's own literal construction-site acceptance criterion.
- Added `qc.report.count_failing()` as the one implementation of the `"FAIL" in c["Status"]`
  count, used by `app.py`'s pre-summary progress narration and internally by
  `LayerSummary.n_fail`/`QcSummary.n_fail`, rather than leaving app.py's five progress lines as
  a sixth, seventh, eighth, ninth and tenth independent re-derivation of the same count.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking] `qc/domain.py` docstring false-positive against Task 1's own verify
command**
- **Found during:** Task 1, running the plan's literal `<verify>` command for the call-site
  scan
- **Issue:** The plan's own verify script (`bad = [str(p) for p in pathlib.Path("qc").glob("*.py")
  if p.name != "__init__.py" and "sort_by_registry" in p.read_text()]`) is a plain substring
  scan, and `qc/domain.py`'s docstring mentioned the literal string `"sort_by_registry"` in
  prose (describing the registry-declared order, not calling anything). This made the verify
  command fail even though no code called `sort_by_registry` from `qc/domain.py`.
- **Fix:** Reworded the docstring sentence ("a registry-declared order (the re-sort helper
  qc/__init__.py exposes) is the load-bearing backstop") to describe the mechanism without
  repeating its call-shaped name. No executable code changed.
- **Files modified:** `qc/domain.py`
- **Verification:** The plan's literal verify command now prints `call-site sort ok`; full
  suite green.
- **Commit:** `ff529be` (Task 1)

**2. [Rule 1/2 — bug / missing critical] `app.py`'s progress narration recomputed a failing
count locally**
- **Found during:** Task 2, writing (and running) the offender-set AST test the task itself
  specifies
- **Issue:** Five lines in `app.py`'s QC execution block (printed live as each of the five
  layers finishes, before the shared `QcSummary` exists) each computed
  `sum(1 for c in <layer>_checks if "FAIL" in c["Status"])` locally — the exact
  local-recomputation shape F1/F6/F8 all took, and something the task's own acceptance
  criterion ("no call in app.py sums over a check-status membership test") explicitly forbids.
- **Fix:** Added `qc.report.count_failing(checks)` as the one shared implementation and called
  it from all five sites; also routed `LayerSummary.n_fail` and `QcSummary.n_fail` through it,
  so the "FAIL" in Status membership test has exactly one implementation across the whole
  codebase instead of six independent copies.
- **Files modified:** `app.py`, `qc/report.py`
- **Verification:** `tests/test_verdict_agreement.py::test_no_offender_recomputes_a_failing_count_or_a_detail_frame_length`
  passes with zero offenders; full suite green (195 passed).
- **Commit:** `18212d7` (Task 2)

**3. [Rule 2 — missing critical] Score table's layer-label lookup named all five layers as
dict keys**
- **Found during:** Task 2, writing (and running) the construction-site companion-invariant
  test the task itself specifies
- **Issue:** Tab 2's score-breakdown table looked up each layer's emoji+label from a local
  `app.py` dict literal (`_LAYER_LABELS`) keyed on all five layer names — exactly the
  "per-layer name literal used as a dictionary key at a presentation construction site" the
  task's companion invariant targets. A future sixth layer would raise `KeyError` at this site
  rather than appearing automatically, since nothing else in the score-table construction
  reads the label from a registry-adjacent source.
- **Fix:** Relocated the dict to `qc.report.LAYER_LABELS`, alongside
  `LAYER_ORDER`/`LAYER_WEIGHTS`/`NOT_RUN_REASON` (which already live there for the same
  reason). `app.py`'s score table now reads `qc.report.LAYER_LABELS[_name]` — the same
  construction shape, but the layer-name-keyed dict itself lives next to the other
  layer-keyed constants, not as a standalone app.py literal.
- **Files modified:** `app.py`, `qc/report.py`
- **Verification:** `tests/test_verdict_agreement.py::test_score_table_metadata_card_and_breakdown_iterate_layer_order_not_named_dict_keys`
  passes with zero offenders; full suite green.
- **Commit:** `18212d7` (Task 2)

---

**Total deviations:** 3 auto-fixed (1 blocking test-authoring/docstring false positive, 2
missing-critical structural fixes the plan's own tests required).
**Impact on plan:** All three fixes are exactly what the plan's own `<verify>`/acceptance
criteria demanded — none expand scope beyond installing the two standing guards this plan
exists to add. No rendered value, sheet, or emailed line changed for any user-visible scenario;
the fixes relocate and consolidate existing logic to a single implementation each.

## Issues Encountered

None beyond the three auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3's two structural guarantees (canonical order everywhere; one verdict/score/count
  computation, four readers) are now standing tests, not conventions — a future phase that
  registers a new rule or adds a sixth layer either satisfies both tests automatically
  (order/appearance) or turns them red immediately.
- README.md §8, §10 and §11 match the shipped scoring, report and email behaviour; a human
  should still skim the rendered Markdown before this phase ships (see coverage D6's rationale).
- `app.py` confirmed still CRLF-terminated after every edit in this plan (checked after each
  task); `qc/report.py`, `qc/domain.py`, `tests/*.py` and `README.md` remain LF.
- Phase 3 is now fully executed (plans 01-04 all summarized): F1, F6, F8, F11, F12, F14 closed;
  VERDICT-01 through VERDICT-06 and ENGINE-08 all complete.

---
*Phase: 03-verdict-and-report-integrity*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All created files found on disk: `tests/test_summary_sheet_order.py`,
  `tests/test_verdict_agreement.py`, this SUMMARY.
- All modified files found on disk: `qc/report.py`, `qc/domain.py`, `app.py`, `README.md`.
- All 3 task commits found in git history: `ff529be`, `18212d7`, `3d020fd`.
- Full suite green: `python3 -m pytest tests/ -q` — 195 passed (178 phase-baseline + 8 new
  from Task 1 + 9 new from Task 2 + 0 new from Task 3's README-only change = 195).
- `python3 -m compileall -q qc app.py tests` — clean (exit 0).
- Plan-level `<verification>` block re-run: full suite (195 passed), compileall (clean),
  the two standing guards together (`test_summary_sheet_order.py` + `test_verdict_agreement.py`,
  17 passed), and the README string-presence/absence check (prints `readme ok`).
- `app.py` confirmed still CRLF-terminated (0 LF-only lines) after every edit in this plan;
  `qc/report.py`, `qc/domain.py`, `tests/*.py` and `README.md` remain LF.
- `git diff --stat README.md` confirmed the edit is scoped to exactly §8/§10/§11's line ranges
  — §2, §3 and §7 (including the two required-columns tables) are untouched.
- `commits: 3` measured via `git rev-list --count 26e7700..HEAD` against the persisted
  `plan_head_before` ledger — matches the three commits listed above exactly.
