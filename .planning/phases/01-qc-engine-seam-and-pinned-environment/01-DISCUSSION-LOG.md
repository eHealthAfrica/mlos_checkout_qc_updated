# Phase 1: QC Engine Seam and Pinned Environment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-09
**Phase:** 1-QC Engine Seam and Pinned Environment
**Areas discussed:** Rule identifier scheme, Existing number stability, Extraction boundary, How ordering is enforced

All four offered areas were selected for discussion.

---

## Rule Identifier Scheme

Question: what replaces the duplicated numbers, given `11a` and `11b` are already taken by
the conflict rules?

| Option | Description | Selected |
|--------|-------------|----------|
| Field-named suffixes | `11.urban`, `11.rural`, `11.scattered`, and `12.highrisk` … `12.fulani`. Self-describing in a report; no collision with existing `11a`/`11b`. Cost: longer strings in a narrow Rule# column, and a new convention alongside the existing letter suffixes. | ✓ |
| Letters continuing from 11c | Field checks become `11c`/`11d`/`11e`; flags become `12a`–`12h`. Existing `11a`/`11b` keep their meaning. Cost: letters stop grouping meaningfully — `11a`/`11b` are conflict checks while `11c`–`11e` are field checks. | |
| Letters, renumbering the conflict rules | urban/rural/scattered become `11a`/`11b`/`11c`, conflict rules move to `11d`/`11e`, flags become `12a`–`12h`. Cleanest grouping. Cost: `11a`/`11b` change meaning, so a filed report citing them would point at a different check. | |

**User's choice:** Field-named suffixes

**Notes:** The collision was surfaced during analysis rather than assumed — enumerating the
31 identifiers actually emitted by `app.py` showed `11a` and `11b` already in use by the two
conflict rules, and `SQ2b` establishing a letter-suffix precedent. Field naming was the only
option that neither invalidated an existing identifier nor produced a grouping where letters
meant two different things. The self-describing property (`12.fulani` needs no lookup table)
was a stated benefit rather than an incidental one.

---

## Existing Number Stability

Question: do the other 27 identifiers keep their exact numbers?

| Option | Description | Selected |
|--------|-------------|----------|
| Freeze all 27 (Recommended) | Only duplicates get new IDs; every other identifier keeps its exact string, so reports already filed stay readable. Scheme stays mixed — bare numbers for MLoS, `S`/`SQ`/`TP`/`B` prefixes elsewhere — but that mix is what people have learned. | ✓ |
| Normalise the whole scheme | Uniform layer prefixes for every rule. Cleaner and easier to extend when Phase 7 adds three layers. Cost: every existing report reference breaks at once, during the milestone whose purpose is making the tool more trustworthy. | |

**User's choice:** Freeze all 27

**Notes:** Rated `one-way` in CONTEXT.md — there is no migration for a printed or emailed
report, so renumbering later would silently repoint an existing reference at a different
check. Normalisation was not rejected on merit and is recorded as a deferred idea for a
milestone boundary where a break is already expected.

---

## Extraction Boundary

Question: how much of `app.py` moves into `qc/` in this phase? (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| The five `run_*_qc()` functions | Already pure DataFrame-in, results-out. The phase's core, in scope either way. | ✓ |
| Constants and `vec_*` helpers | `VALID_*`, `UUID_RE`, `EDITOR_RE`, `YN_NA_COLS`, `MLOS_REQUIRED_COLS`, plus `vec_is_uuid`, `vec_is_editor`, `pct`. Flagged as near-forced when offered. | ✓ (on follow-up) |
| `auto_correct_mlos()` | Equally pure, but its F4/F5 defects are Phase 2 work — moving it now means Phase 2 edits a file Phase 1 just created. | ✓ |
| The loaders | `load_csv`, `load_xlsx`, `load_sqlite`, `get_uploaded_data`. The last touches `st.session_state`, so including them means splitting pure parsing from the caching wrapper. | |

**User's choice:** The five `run_*_qc()` functions + `auto_correct_mlos()`; constants and
helpers added after a follow-up; loaders excluded.

**Notes:** The initial selection excluded the constants and helpers. A dependency check was
run rather than asserting a preference, and it showed all six moving functions reference at
least one left-behind symbol — every `run_*_qc()` needs `pct`, and `run_mlos_qc` needs five
constants plus both predicates. Leaving them would have required `qc/` to `import app`,
making Phase 1's third success criterion ("`import qc` succeeds with Streamlit uninstalled")
unachievable. This was raised as a conflict with a success criterion, not as a disagreement
about taste.

### Follow-up: dependency handling

| Option | Description | Selected |
|--------|-------------|----------|
| Move them too (Recommended) | Constants to `qc/domain.py`, predicates and `pct` to `qc/predicates.py`. Makes criterion 3 achievable; `qc/` becomes genuinely self-contained. | ✓ |
| Inject them as parameters | Keep in `app.py`, pass into each rule function. Satisfies the no-streamlit rule but changes all six signatures and threads a dozen arguments through for no benefit. | |
| Leave them and drop criterion 3 | Accept `qc/` importing `app.py` and amend the phase's success criteria. Honest about the consequence, but forfeits the seam ENGINE-05 exists to create, which Phases 6 and 7 both assume. | |

**User's choice:** Move them too

**Notes:** `auto_correct_mlos()` moving in this phase is a deliberate accepted tradeoff, not
an oversight — recorded as D-09 so the planner does not "optimise" it away by deferring the
move to Phase 2.

---

## How Ordering Is Enforced

Question: how is deterministic emission order enforced?

| Option | Description | Selected |
|--------|-------------|----------|
| Both (Recommended) | `YN_NA_COLS` becomes a tuple — matching `FLAG_COLS`, already an ordered list of nearly the same columns — and the registry imposes order at emission. The tuple fixes today's defect in the existing idiom; the registry guarantee is what ENGINE-02's standing test asserts. | ✓ |
| Tuple only | Smallest change, matches convention exactly. But nothing structural stops the next contributor declaring a new set and reopening the defect. | |
| Registry ordering only | One enforcement point, `YN_NA_COLS` stays a set. But order then depends entirely on the sort key being right, and a naive lexicographic sort would order rules `1, 10, 11, 2` — worse than today. | |

**User's choice:** Both

**Notes:** The `FLAG_COLS`-is-already-a-list observation came from reading
`.planning/codebase/CONVENTIONS.md` during the codebase scout, and it turns the tuple change
from a new convention into conformance with an existing one. `FLAG_COLS` (`app.py:695`) and
`YN_NA_COLS` (`app.py:100`) hold nearly the same flag columns, one ordered and one not.

---

## Claude's Discretion

Recorded in CONTEXT.md for the planner rather than decided here:

- **Registry sort semantics.** "Both" settles that the registry imposes order but not by what
  key. Recommended: layer order, then declaration order within a layer, preserving the
  current display sequence and satisfying Phase 3's VERDICT-06 (`B0, B1, B2, B3`). Flagged as
  an implementation detail for the planner to confirm against the code, not a user preference.
- **Module naming.** `qc/domain.py` and `qc/predicates.py` are suggestions consistent with the
  repo's snake_case convention; the planner may choose better names.
- **`qc/__init__.py` surface.** Whether it re-exports a `run_all()` façade or callers import
  each module directly.

## Deferred Ideas

- **Normalising the whole identifier scheme** with uniform layer prefixes — rejected for M1 to
  preserve report continuity. More attractive once Phase 7 adds three further layers.
- **Loader extraction** — splitting the loaders into pure parsing plus a Streamlit caching
  wrapper. Belongs in Phase 2, which changes loader behaviour anyway via INTEG-01/INTEG-03.
- **Linter and formatter configuration.** No `.flake8`, `.pylintrc` or `pyproject.toml` exists.
  Reasonable alongside dependency pinning but not in any requirement, so not smuggled in.

## Scope Discipline

No scope creep arose. All four areas clarified how to implement what the roadmap already
scoped; the three deferred items above were recorded rather than acted on.
