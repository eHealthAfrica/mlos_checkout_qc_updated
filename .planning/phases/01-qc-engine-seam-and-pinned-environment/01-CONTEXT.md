# Phase 1: QC Engine Seam and Pinned Environment - Context

**Gathered:** 2026-09-09
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the structural seam the rule set lives in: one identity scheme where
every check has an identifier naming exactly one check, one stable emission order, a `qc/`
package importable without Streamlit, and one pinned dependency set.

It delivers **no new checks and no changed verdicts**. A submission that passes today must
produce the same findings after this phase — only their identifiers and their order change.
Detection correctness (Phase 2) and report/verdict coverage (Phase 3) are explicitly not
this phase's work.

</domain>

<decisions>
## Implementation Decisions

### Rule Identifier Scheme

- **D-01:** The 11 checks currently sharing two numbers get **field-named suffixes**, not letter suffixes. Rule 11's three field checks become `11.urban`, `11.rural`, `11.scattered`. Rule 12's eight profile-flag checks become `12.highrisk`, `12.slums`, `12.densely_populated`, `12.hard2reach`, `12.border`, `12.nomadic`, `12.riverine`, `12.fulani`. — **Reversibility:** costly — the identifier is the join key between check records and detail rows, and it is printed in every on-screen summary table, every per-rule Excel sheet name, the emailed summary, and the sidebar rules-reference tables. Changing the scheme again means touching all of those plus any report the data team has filed in the interim.
- **D-02:** Field-named suffixes were chosen over letters specifically because **`11a` and `11b` are already taken** by the two conflict rules ("Cannot be both Urban and Rural", "Urban cannot be Scattered"). A letter scheme would have forced either a meaningless grouping (field checks at `11c`–`11e`, conflict checks at `11a`/`11b`) or renumbering `11a`/`11b` and invalidating existing report references. The field-named scheme sidesteps both.
- **D-03:** A secondary benefit, and part of why this was chosen: the identifier is self-describing. An officer reading `12.fulani` in a report knows which field failed without consulting the rules-reference table.

### Existing Identifier Stability

- **D-04:** All 27 existing identifiers are **frozen exactly as they are**. Only the duplicated ones get new IDs. `1`–`10`, `11a`, `11b`, `13`, `14`, `S1`, `S2`, `SQ1`, `SQ2`, `SQ2b`, `SQ3`, `SQ4`, `TP2`–`TP5`, `B0`–`B3` keep their exact strings. — **Reversibility:** one-way — reports the data team has already filed cite these identifiers, and there is no migration for a printed or emailed report. Renumbering later would silently repoint an existing reference at a different check.
- **D-05:** Normalising the whole scheme with uniform layer prefixes was considered and **rejected for M1**. The mixed scheme (bare numbers for MLoS, `S`/`SQ`/`TP`/`B` prefixes elsewhere) is what people have already learned, and M1's purpose is to make the tool more trustworthy, not less familiar. Recorded as a deferred idea for a milestone boundary where a break is already expected.

### Extraction Boundary

- **D-06:** Moving into `qc/` in this phase: the five `run_*_qc()` functions (`run_schema_qc`, `run_mlos_qc`, `run_settlement_qc`, `run_takeoff_qc`, `run_ward_boundary_qc`) **and** `auto_correct_mlos()`.
- **D-07:** The domain constants and vectorised helpers move too, into `qc/domain.py` (`VALID_DAY`, `VALID_YN`, `VALID_YN_NA`, `VALID_ACC`, `VALID_HAB`, `YN_NA_COLS`, `FLAG_COLS`, `UUID_RE`, `EDITOR_RE`, `MLOS_REQUIRED_COLS`, `TAKEOFF_REQUIRED_COLS`) and `qc/predicates.py` (`vec_is_uuid`, `vec_is_editor`, `pct`). **This is forced, not preferential** — verified by dependency check, every one of the six moving functions references at least one of these symbols:

  | Moving function | Depends on |
  |---|---|
  | `run_schema_qc` | `MLOS_REQUIRED_COLS`, `TAKEOFF_REQUIRED_COLS`, `pct` |
  | `run_mlos_qc` | `VALID_ACC`, `VALID_HAB`, `VALID_YN_NA`, `VALID_YN`, `YN_NA_COLS`, `vec_is_uuid`, `vec_is_editor`, `pct` |
  | `run_settlement_qc` | `pct` |
  | `run_takeoff_qc` | `vec_is_uuid`, `pct` |
  | `run_ward_boundary_qc` | `pct` |
  | `auto_correct_mlos` | `FLAG_COLS`, `vec_is_uuid` |

  Leaving them in `app.py` would require `qc/` to `import app`, which imports Streamlit — making success criterion 3 ("`import qc` succeeds in an interpreter with Streamlit uninstalled") unachievable and failing ENGINE-05's test. Parameter injection was considered and rejected: it changes all six signatures and threads a dozen arguments through for no benefit.

- **D-08:** The loaders **stay in `app.py`** for this phase — `load_csv`, `load_xlsx`, `load_sqlite`, `get_uploaded_data`. `get_uploaded_data` reads and writes `st.session_state`, so it cannot enter `qc/` unchanged; separating pure parsing from the caching wrapper is real work, and Phase 2 changes loader behaviour anyway via INTEG-01 and INTEG-03. Deferred to Phase 2.
- **D-09:** **Accepted tradeoff, stated explicitly:** `auto_correct_mlos()` moves in this phase even though its two defects (F4 cache divergence, F5 non-deterministic GUIDs) are Phase 2 work — so Phase 2 will edit a file Phase 1 has just created. The user chose this deliberately so that all pure code lands on the correct side of the seam in one move rather than leaving one pure function stranded. The planner should not treat this as an oversight to "optimise" by deferring the move.

### Deterministic Emission Order

- **D-10:** Order is enforced at **both** levels. `YN_NA_COLS` becomes an ordered collection (tuple), and the registry additionally imposes order at emission time.
- **D-11:** The tuple change matches existing convention rather than introducing a new one: `FLAG_COLS` is already an ordered list of nearly the same flag columns, at `app.py:695`. `YN_NA_COLS` being a set at `app.py:100` is the anomaly.
- **D-12:** The registry-side guarantee is the load-bearing half, because it is what ENGINE-02's standing test can assert cheaply — a future contributor declaring a new set literal cannot silently reintroduce the defect. A tuple alone fixes today's symptom but leaves nothing structural preventing recurrence.

### Claude's Discretion

- **Registry sort semantics.** D-10 says the registry imposes order but not by what key. A naive lexicographic sort would order rules `1, 10, 11, 2` — worse than today. The planner should use **layer order, then declaration order within a layer**, preserving the current display sequence (Schema → MLoS → Settlement → Takeoffpoint → Boundary). This also satisfies Phase 3's VERDICT-06, which requires boundary checks to read `B0, B1, B2, B3`. Flagged rather than decided, because it is an implementation detail the planner should confirm against the code, not a user preference.
- **Module naming.** `qc/domain.py` and `qc/predicates.py` are suggested names consistent with the repo's snake_case single-word file convention. The planner may choose better ones; the requirement is that they live under `qc/` and contain no Streamlit import.
- **`__init__.py` surface.** Whether `qc/__init__.py` re-exports a `run_all()` façade or callers import each module directly. Architecture research suggested `app.py` calls `qc.run_all()`; the planner decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 1 section: goal, five success criteria, and the ENGINE-09 placement evidence with line anchors
- `.planning/REQUIREMENTS.md` — ENGINE-01, ENGINE-02, ENGINE-05, ENGINE-07, ENGINE-09 (the five requirements this phase closes)
- `.planning/PROJECT.md` — Core Value, constraints, Key Decisions table
- `.planning/STATE.md` — accumulated decisions and per-phase blockers

### Technical grounding
- `.planning/research/ARCHITECTURE.md` — rule registry pattern, `qc/` module layout, the no-`import streamlit`-in-`qc/` rule and how to enforce it by test, why Great Expectations/soda-core machinery is over-engineering here
- `.planning/research/STACK.md` — `pandas==3.0.5` pin rationale and the 3.0 breaking changes that hit this codebase: default `str` dtype (breaks `dtype == "object"` checks), stricter `setitem` typing, Copy-on-Write by default, Python ≥3.11 floor
- `.planning/research/SUMMARY.md` — the four resolved cross-agent conflicts and the suggested phase shape
- `.planning/codebase/CONVENTIONS.md` — naming patterns; note that module-level constants are UPPERCASE with underscores and files are lowercase snake_case

### Subject code
- `app.py` — the file being restructured. Specific anchors: `YN_NA_COLS` set literal at `:100`, iterated at `:946`; the R11 loop at `:927`; `FLAG_COLS` ordered list at `:695`; the five `run_*_qc()` functions at `:232`, `:539`, `:805`, `:969`, `:383`; `auto_correct_mlos()` at `:700`; `pct` at `:207`; `vec_is_uuid`/`vec_is_editor` at `:210`/`:214`
- `requirements.txt` — currently `pandas>=2.0.0` unbounded, resolving to 3.0.2 in the live environment; `numpy` imported at `app.py:540` but never declared

**No external ADRs or specs exist** for this project — no `/gsd-spec-phase` run, no ingested ADRs. Requirements are fully captured in the decisions above and in `REQUIREMENTS.md`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The five `run_*_qc()` functions are already pure** — DataFrame in, `(checks_list, detail_dataframe)` out. This is why extraction is tractable rather than a rewrite, and it is the single most important fact about this phase. `TESTING.md` claims Streamlit coupling prevents testing; that is true of the UI, not of these functions.
- **`add()` closure**, duplicated verbatim inside each of the five functions, builds every check record. It is the natural thing to replace with one shared registry helper — and replacing it is what fixes ENGINE-01 and ENGINE-09 together.
- **`FLAG_COLS` at `app.py:695`** is an already-ordered list of nearly the same columns as `YN_NA_COLS`. The ordering fix has a convention to follow, not to invent.

### Established Patterns
- Module-level constants are UPPERCASE with underscores, declared near the top after imports. `qc/domain.py` should preserve that.
- Every rule is guarded on column presence (`if col in mlos.columns`), so a partial file degrades rather than crashes. Extraction must preserve this — but note it degrades *silently*, which is Phase 2's INTEG-03 problem, not this phase's to fix.
- Regex checks are vectorised via `str.match` rather than per-row `apply`. Keep them that way.
- No formatter, linter, or `pyproject.toml` exists. This phase introduces `requirements.txt` pins; whether to add tooling config is out of scope.

### Integration Points
- `app.py` becomes presentation and orchestration only: load → call into `qc/` → score → render → export. Everything the rules need moves behind the seam.
- The rule identifier is the join key between `checks` and `detail` rows. Three consumers read it and all must follow the new scheme: `make_longitudinal_df` at `:316` (`mlos_detail["Rule#"] == rn`), the per-rule drilldown expanders in tabs 3–6, and the per-rule Excel sheet naming (`f"Rule {rn}"[:31]`).
- Sheet-name length: `f"Rule {rn}"` is truncated to Excel's 31-character limit. Verified: the longest new identifier, `12.densely_populated`, yields `Rule 12.densely_populated` at 25 characters — comfortably within the limit, so no sheet name overflows.
- The sidebar rules-reference tables at `:1205`–`:1279` document rule numbers as static markdown and must be updated to match the new identifiers, or the reference and the reports disagree.

</code_context>

<specifics>
## Specific Ideas

- Identifiers should read as `12.fulani` — a dotted field name, not a letter. The user explicitly valued that an officer can see which field failed straight from the identifier.
- Nothing an officer already knows should break. Freezing the 27 existing identifiers was chosen over a cleaner uniform scheme for exactly this reason.

</specifics>

<deferred>
## Deferred Ideas

- **Normalising the whole identifier scheme** with uniform layer prefixes so identity is consistent across all layers. Rejected for M1 to preserve continuity with reports the data team has filed. Worth revisiting at a milestone boundary where a break is already expected — and more attractive once Phase 7 adds three further layers to a scheme that is already mixed.
- **Loader extraction** — splitting `load_csv` / `load_xlsx` / `load_sqlite` / `get_uploaded_data` into pure parsing plus a Streamlit caching wrapper. Belongs in Phase 2, which changes loader behaviour anyway via INTEG-01 (format-independent null detection) and INTEG-03 (column-name normalisation at load).
- **Linter and formatter configuration.** The repo has no `.flake8`, `.pylintrc` or `pyproject.toml`. Adding tooling would be reasonable alongside dependency pinning but is not in any requirement, so it is not being smuggled into this phase.

</deferred>

---

*Phase: 1-QC Engine Seam and Pinned Environment*
*Context gathered: 2026-09-09*
