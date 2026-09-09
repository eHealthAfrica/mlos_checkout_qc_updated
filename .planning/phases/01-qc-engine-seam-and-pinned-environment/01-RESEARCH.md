# Phase 1: QC Engine Seam and Pinned Environment - Research

**Researched:** 2026-09-09
**Domain:** Python package extraction (rule registry pattern), dependency pinning, deterministic-order testing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rule Identifier Scheme**
- **D-01:** The 11 checks currently sharing two numbers get **field-named suffixes**, not letter suffixes. Rule 11's three field checks become `11.urban`, `11.rural`, `11.scattered`. Rule 12's eight profile-flag checks become `12.highrisk`, `12.slums`, `12.densely_populated`, `12.hard2reach`, `12.border`, `12.nomadic`, `12.riverine`, `12.fulani`. — **Reversibility:** costly — the identifier is the join key between check records and detail rows, and it is printed in every on-screen summary table, every per-rule Excel sheet name, the emailed summary, and the sidebar rules-reference tables. Changing the scheme again means touching all of those plus any report the data team has filed in the interim.
- **D-02:** Field-named suffixes were chosen over letters specifically because **`11a` and `11b` are already taken** by the two conflict rules ("Cannot be both Urban and Rural", "Urban cannot be Scattered"). A letter scheme would have forced either a meaningless grouping (field checks at `11c`–`11e`, conflict checks at `11a`/`11b`) or renumbering `11a`/`11b` and invalidating existing report references. The field-named scheme sidesteps both.
- **D-03:** A secondary benefit, and part of why this was chosen: the identifier is self-describing. An officer reading `12.fulani` in a report knows which field failed without consulting the rules-reference table.

**Existing Identifier Stability**
- **D-04:** All 27 existing identifiers are **frozen exactly as they are**. Only the duplicated ones get new IDs. `1`–`10`, `11a`, `11b`, `13`, `14`, `S1`, `S2`, `SQ1`, `SQ2`, `SQ2b`, `SQ3`, `SQ4`, `TP2`–`TP5`, `B0`–`B3` keep their exact strings. — **Reversibility:** one-way — reports the data team has already filed cite these identifiers, and there is no migration for a printed or emailed report. Renumbering later would silently repoint an existing reference at a different check.
- **D-05:** Normalising the whole scheme with uniform layer prefixes was considered and **rejected for M1**. The mixed scheme (bare numbers for MLoS, `S`/`SQ`/`TP`/`B` prefixes elsewhere) is what people have already learned, and M1's purpose is to make the tool more trustworthy, not less familiar. Recorded as a deferred idea for a milestone boundary where a break is already expected.

**Extraction Boundary**
- **D-06:** Moving into `qc/` in this phase: the five `run_*_qc()` functions (`run_schema_qc`, `run_mlos_qc`, `run_settlement_qc`, `run_takeoff_qc`, `run_ward_boundary_qc`) **and** `auto_correct_mlos()`.
- **D-07:** The domain constants and vectorised helpers move too, into `qc/domain.py` (`VALID_DAY`, `VALID_YN`, `VALID_YN_NA`, `VALID_ACC`, `VALID_HAB`, `YN_NA_COLS`, `FLAG_COLS`, `UUID_RE`, `EDITOR_RE`, `MLOS_REQUIRED_COLS`, `TAKEOFF_REQUIRED_COLS`) and `qc/predicates.py` (`vec_is_uuid`, `vec_is_editor`, `pct`). **This is forced, not preferential** — verified by dependency check, every one of the six moving functions references at least one of these symbols. Leaving them in `app.py` would require `qc/` to `import app`, which imports Streamlit — making success criterion 3 unachievable. Parameter injection was considered and rejected: it changes all six signatures for no benefit.
- **D-08:** The loaders **stay in `app.py`** for this phase — `load_csv`, `load_xlsx`, `load_sqlite`, `get_uploaded_data`. `get_uploaded_data` reads and writes `st.session_state`, so it cannot enter `qc/` unchanged; Phase 2 changes loader behaviour anyway via INTEG-01 and INTEG-03. Deferred to Phase 2.
- **D-09:** **Accepted tradeoff, stated explicitly:** `auto_correct_mlos()` moves in this phase even though its two defects (F4 cache divergence, F5 non-deterministic GUIDs) are Phase 2 work — so Phase 2 will edit a file Phase 1 has just created. The user chose this deliberately so that all pure code lands on the correct side of the seam in one move. The planner should not treat this as an oversight to "optimise" by deferring the move.

**Deterministic Emission Order**
- **D-10:** Order is enforced at **both** levels. `YN_NA_COLS` becomes an ordered collection (tuple), and the registry additionally imposes order at emission time.
- **D-11:** The tuple change matches existing convention rather than introducing a new one: `FLAG_COLS` is already an ordered list of nearly the same flag columns, at `app.py:695`. `YN_NA_COLS` being a set at `app.py:100` is the anomaly.
- **D-12:** The registry-side guarantee is the load-bearing half, because it is what ENGINE-02's standing test can assert cheaply — a future contributor declaring a new set literal cannot silently reintroduce the defect. A tuple alone fixes today's symptom but leaves nothing structural preventing recurrence.

### Claude's Discretion

- **Registry sort semantics.** D-10 says the registry imposes order but not by what key. A naive lexicographic sort would order rules `1, 10, 11, 2` — worse than today. The planner should use **layer order, then declaration order within a layer**, preserving the current display sequence (Schema → MLoS → Settlement → Takeoffpoint → Boundary). This also satisfies Phase 3's VERDICT-06, which requires boundary checks to read `B0, B1, B2, B3`. Flagged rather than decided, because it is an implementation detail the planner should confirm against the code, not a user preference.
- **Module naming.** `qc/domain.py` and `qc/predicates.py` are suggested names consistent with the repo's snake_case single-word file convention. The planner may choose better ones; the requirement is that they live under `qc/` and contain no Streamlit import.
- **`__init__.py` surface.** Whether `qc/__init__.py` re-exports a `run_all()` façade or callers import each module directly. Architecture research suggested `app.py` calls `qc.run_all()`; the planner decides.

### Deferred Ideas (OUT OF SCOPE)

- **Normalising the whole identifier scheme** with uniform layer prefixes so identity is consistent across all layers. Rejected for M1 to preserve continuity with reports the data team has filed. Worth revisiting at a milestone boundary where a break is already expected — and more attractive once Phase 7 adds three further layers to a scheme that is already mixed.
- **Loader extraction** — splitting `load_csv` / `load_xlsx` / `load_sqlite` / `get_uploaded_data` into pure parsing plus a Streamlit caching wrapper. Belongs in Phase 2, which changes loader behaviour anyway via INTEG-01 (format-independent null detection) and INTEG-03 (column-name normalisation at load).
- **Linter and formatter configuration.** The repo has no `.flake8`, `.pylintrc` or `pyproject.toml`. Adding tooling would be reasonable alongside dependency pinning but is not in any requirement, so it is not being smuggled into this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| ENGINE-01 | Every check carries a rule identifier that is unique across all layers — closes F3 | Pattern 1 (Import-Time Rule Registry): frozen `Rule` dataclass + `register()` catches collisions; D-01's exact field-named ids for the 11 colliding checks are reproduced verbatim in the R11/R12 code examples |
| ENGINE-02 | Rule identifier uniqueness is enforced when the rule registry is imported, and is covered by a standing test so the defect cannot reopen as the rule set grows | Pattern 1's `register()` raises `ValueError` at import time, independent of any DataFrame processing; standing test in Code Examples (`test_duplicate_rule_id_raises_at_registration`, `test_current_ruleset_has_no_duplicates`) |
| ENGINE-05 | All QC layers live in a `qc/` package containing no `import streamlit`, enforced by a test | Architectural Responsibility Map + D-07's dependency table (verified forced, not preferential); AST-based guard test in Code Examples; Environment Availability notes streamlit is absent from this dev environment, making the criterion directly verifiable here |
| ENGINE-07 | Dependencies are pinned with an upper bound, including `pandas==3.0.5` and an explicit `numpy` declaration | Standard Stack section — all six package versions (pandas, numpy, streamlit, openpyxl, xlrd, pytest) verified live against PyPI in this session; final `requirements.txt` given in Code Examples; Assumption A1 flags the upper-bound scope question |
| ENGINE-09 | Rule emission order is deterministic across application restarts, so two reports over identical data can be diffed row-for-row — closes F10 | Pattern 2 (two-level fix: tuple + registry-declared canonical order) and Pattern 3 (subprocess-based test is the only valid way to prove cross-process determinism); Pitfall 2 restates why an in-process test is insufficient |

</phase_requirements>

## Summary

Phase 1 is a pure structural refactor: no new checks, no changed verdicts, no new external
dependencies. Everything needed to plan it precisely already exists in the codebase (read
directly, line-by-line, in this research session) and in two upstream documents this research
treats as authoritative: `01-CONTEXT.md` (locked user decisions) and the project's own prior
`ARCHITECTURE.md`/`STACK.md` research (already HIGH-confidence, produced the same day from
official docs and direct PyPI verification).

The five `run_*_qc()` functions are already pure — `DataFrame` in, `(checks, detail_df)` out —
which is why this extraction is tractable in one phase rather than a rewrite. The two defects
this phase closes (F3 duplicate rule numbers, F10 non-deterministic order) trace to the exact
same eight lines of code: `YN_NA_COLS` is a `set` literal at `app.py:100-101`, iterated at
`app.py:946` inside a loop that calls `add("12", ...)` for all eight columns — so every one of
those eight checks currently carries both defects at once. A tuple conversion plus a small
import-time rule registry (a frozen `Rule` dataclass registered via a `register()` function
that raises `ValueError` on a duplicate id) fixes both defects with one mechanism, matches the
codebase's own existing convention (`FLAG_COLS` is already an ordered list at `app.py:695`), and
requires no new runtime dependency.

Verified directly against PyPI in this session: `pandas==3.0.5` and a `numpy>=2.0.0,<3.0.0`
floor are available now and match the exact-pin decision already recorded in `STACK.md`. This
codebase's loaders already force `dtype=str` on every load path, and a direct grep of `app.py`
found zero `dtype == "object"` comparisons and zero chained-assignment (`df[mask][col] = `)
patterns — the two pandas-3.0 breaking-change classes `STACK.md` flagged as highest-risk. That
lowers the migration risk from "unknown" to "specifically checked and clean," though the
extracted `qc/` modules should be re-checked post-move since line numbers and surrounding code
will shift.

**Primary recommendation:** Build a single `qc/results.py` registry (frozen `Rule` dataclass +
`register()` that raises on duplicate id, populated at **import time**, independent of any
DataFrame ever being processed) as the seam every extracted layer registers against; convert
`YN_NA_COLS` to a tuple and give the R11/R12 loops field-named identifiers exactly as specified
in `01-CONTEXT.md` D-01; pin `pandas==3.0.5` and declare `numpy>=2.0.0,<3.0.0` (plus upper
bounds on the three existing loose pins) in `requirements.txt`; and add a minimal `pytest`
harness (not yet present anywhere in this repo) whose three new tests directly assert the three
testable success criteria (duplicate-id rejection, no-streamlit-import, cross-process order
stability).

## Architectural Responsibility Map

This project has no browser/API/CDN tiers — it is a single-process Python script. The
project-specific tiers that actually exist (per this project's own `ARCHITECTURE.md`) are used
below instead of forcing a web-app tier vocabulary onto a monolithic data-processing app.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rule identity (unique id, name, description) | `qc/results.py` (registry) | — | Must exist independent of any runtime DataFrame; the only place that can enforce global uniqueness at import time (ENGINE-01/02) |
| Deterministic check-emission order | `qc/results.py` (registry, declares canonical order) | `qc/mlos.py` (iterates ordered tuples, not sets) | Registry order is the structural guarantee (D-12); tuple conversion is the immediate symptom fix — both are needed |
| Rule execution (mask logic, pass/fail) | `qc/<layer>.py` (5 files, pure functions) | — | Already pure per the existing codebase map; only relocated, not rewritten (D-09 explicitly forbids logic changes here) |
| Domain constants & vectorized predicates | `qc/domain.py`, `qc/predicates.py` | — | Forced by dependency, not preference — every moving function references at least one (verified in `01-CONTEXT.md` D-07's table) |
| File loading (`load_csv`/`load_xlsx`/`load_sqlite`/`get_uploaded_data`) | `app.py` (orchestration) | — | `get_uploaded_data` reads/writes `st.session_state` — cannot enter `qc/` unchanged (D-08); deferred to Phase 2 |
| Streamlit-free import boundary | `qc/` package as a whole | test suite (`tests/test_no_streamlit_in_qc.py`) | Enforced by both the package's own import graph and a standing guard test — belt and suspenders |
| Dependency resolution / reproducible install | `requirements.txt` (environment) | `tests/` (a smoke assertion) | `pip install` behavior is not a runtime capability of any Python module — it is a build-time contract, tested by asserting the installed version, not by unit-testing application code |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pandas` | `==3.0.5` | DataFrame-heavy QC engine (existing) | Currently `>=2.0.0` with no upper bound — this is exactly how the repo silently resolved 3.0.2 in this session's own environment check. `3.0.5` confirmed current on PyPI in this session `[VERIFIED: pip index versions pandas — ran 2026-09-09, LATEST: 3.0.5]`. Pandas 3.0 requires Python `>=3.11` `[CITED: STACK.md, sourced from pandas whatsnew via Context7]`. |
| `numpy` | `>=2.0.0,<3.0.0` | Vectorized haversine math (SQ4) | Imported at `app.py:540` (`import numpy as np`, function-local) but never declared in `requirements.txt` `[VERIFIED: app.py:540]`. Latest on PyPI is `2.5.3` in this session `[VERIFIED: pip index versions numpy — ran 2026-09-09]`; capping `<3.0.0` avoids opting into an untested numpy major version, matching `STACK.md`'s existing recommendation. |

### Existing dependencies needing upper bounds (ENGINE-07's general clause, not just the two named packages)

| Library | Current pin | Recommended pin | Why |
|---------|-------------|------------------|-----|
| `streamlit` | `>=1.32.0` | `>=1.32.0,<2.0.0` | Latest on PyPI is `1.63.0` in this session `[VERIFIED: pip index versions streamlit]`. No upper bound today means a future `2.0` (should one ship) resolves silently, same failure class ENGINE-07 exists to close. |
| `openpyxl` | `>=3.1.0` | `>=3.1.0,<4.0.0` | Latest is `3.1.5` `[VERIFIED: pip index versions openpyxl]`. Already flagged as an at-risk unbounded dependency in this project's own `codebase/CONCERNS.md`. |
| `xlrd` | `>=2.0.1` | `>=2.0.1,<3.0.0` | Latest is `2.0.2` `[VERIFIED: pip index versions xlrd]`. Legacy `.xls` support, low release cadence — upper bound is cheap insurance. |

ENGINE-07's text says "Dependencies are pinned with an upper bound, **including** pandas and
numpy" — read as: all four existing dependencies get bounded, with pandas/numpy singled out
because they are the two currently causing observed problems (drift + non-declaration). Treat
the streamlit/openpyxl/xlrd bounds as in-scope for this phase's `requirements.txt` edit, not
optional — but flag this reading to the planner since the requirement's literal text names
only two packages `[ASSUMED — see Assumptions Log A1]`.

### Supporting (test infrastructure — currently absent entirely)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.0.0,<10.0.0` | Standing tests for ENGINE-02/05/09 | No test framework exists anywhere in this repo today `[VERIFIED: TESTING.md "Framework: Not detected"; confirmed by `find` in this session finding no `conftest.py`/`pytest.ini`/`pyproject.toml`]`. Locally available at `9.0.3` in this session's dev environment `[VERIFIED: python3 -m pytest --version]`; latest on PyPI is `9.1.1`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain pinned `requirements.txt` | `pip-tools`/`poetry` lockfile | No build tooling exists in this repo (`codebase/CONVENTIONS.md`: no `pyproject.toml`, no formatter, no linter). Introducing a lockfile toolchain is a bigger surface change than ENGINE-07 asks for; a hand-pinned `requirements.txt` with explicit bounds already gives reproducibility. Revisit only if dependency count grows much further (M3 adds `shapely`, `huggingface_hub`). |
| `pytest` in `requirements.txt` directly | Separate `requirements-dev.txt` (`-r requirements.txt` + `pytest`) | Keeps the Space's production install lean (Streamlit Cloud/HF Space `pip install -r requirements.txt` wouldn't need to also pull pytest). This repo has no dev/prod split today — introducing one is a small new convention; flagged as a planner decision, not a hard requirement. |
| AST-based streamlit-import guard | Plain `grep -rl streamlit qc/` | `grep` is a one-line MVP and catches every practical case (nobody is going to obfuscate `import streamlit` inside this codebase). AST (`ast.walk` checking for `ast.Import`/`ast.ImportFrom` nodes) is more precise against renamed imports (`import streamlit as st2`) and is what `ARCHITECTURE.md` already recommended — use AST if the planner wants zero false negatives; grep is acceptable if the planner wants the simplest possible test. |

**Installation:**
```bash
pip install "pandas==3.0.5" "numpy>=2.0.0,<3.0.0"
pip install "streamlit>=1.32.0,<2.0.0" "openpyxl>=3.1.0,<4.0.0" "xlrd>=2.0.1,<3.0.0"
pip install "pytest>=8.0.0,<10.0.0"   # dev-only; see Alternatives Considered
```

**Version verification (already performed in this session):**
```
$ python3 -m pip index versions pandas    # INSTALLED: 3.0.2   LATEST: 3.0.5
$ python3 -m pip index versions numpy     # INSTALLED: 2.4.4   LATEST: 2.5.3
$ python3 -m pip index versions streamlit #                    LATEST: 1.63.0 (not installed locally)
$ python3 -m pip index versions openpyxl  #                    LATEST: 3.1.5
$ python3 -m pip index versions xlrd      #                    LATEST: 2.0.2
$ python3 -m pip index versions pytest    # INSTALLED: 9.0.3   LATEST: 9.1.1
```
All version numbers above are `[VERIFIED: pip index versions <pkg>, run 2026-09-09]` against the
live PyPI registry, not training data.

## Package Legitimacy Audit

The seam's automated check (`gsd_run query package-legitimacy check --ecosystem pypi pandas
numpy pytest`) flagged all three as `SUS`. Read the reasons before treating this as a real risk
signal — they are metadata gaps in the check's PyPI data source, not evidence of typosquatting:

| Package | Registry | Signals returned by seam | Verdict | Disposition |
|---------|----------|---------------------------|---------|-------------|
| `pandas` | PyPI | `weeklyDownloads: null`, `repoUrl: null`, reasons: `unknown-downloads`, `no-repository` | SUS | **Approved — heuristic false positive.** Foundational data-analysis package, first released 2008, tens of millions of weekly downloads independently well known; already a production dependency of this app today (only the pin is changing, not the package). `checkpoint:human-verify` still required by protocol before the version bump ships, but this is a rubber-stamp given the package is already in use. |
| `numpy` | PyPI | `too-new` (misreads latest-release date as package age), `unknown-downloads`, `no-repository` | SUS | **Approved — heuristic false positive.** Foundational scientific-Python array library, in continuous use since 2006; already imported by this codebase (`app.py:540`) today, just not yet declared. `checkpoint:human-verify` required before `requirements.txt` is edited to declare it explicitly. |
| `pytest` | PyPI | `repoUrl: github.com/pytest-dev/pytest` (found), reasons: `unknown-downloads` only | SUS | **Approved — heuristic false positive.** The standard Python test framework; the seam itself found the canonical GitHub org/repo. `checkpoint:human-verify` required since this is a genuinely new addition to the project (no test framework exists today). |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** pandas, numpy, pytest — all three dispositioned
above as heuristic false positives; the planner must still add a `checkpoint:human-verify` task
before each is installed/pinned, per protocol, even though the investigation above is already
complete.

`streamlit`, `openpyxl`, `xlrd` were not run through the legitimacy check — they are unchanged,
already-running production dependencies; only their version bound is being tightened, not their
identity.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────── BEFORE (today) ───────────────────────────────┐
│  app.py (1,962 lines) — UI, orchestration, AND all rule logic, in one file    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │run_schema_qc │ │run_mlos_qc   │ │run_settlement│ │run_takeoff_qc│  ...    │
│  │(232-278)     │ │(805-965)     │ │_qc (539-633) │ │(969-1012)    │         │
│  │  add() ──┐   │ │  add() ──┐   │ │  add() ──┐   │ │  add() ──┐   │         │
│  └──────────┼───┘ └──────────┼───┘ └──────────┼───┘ └──────────┼───┘         │
│    5 copy-pasted add() closures, each keying results to a bare "Rule#" str   │
│    YN_NA_COLS = {set literal} ── iterated at :946 ── hash-order per process  │
│  import streamlit  ← pulled in by every function in the file, including QC   │
└────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────── AFTER (Phase 1) ──────────────────────────────┐
│  app.py — orchestration + UI only                                            │
│    │ calls (plain function calls, DataFrames in/out — no change to call     │
│    │  sites' inputs/outputs, only where the functions physically live)       │
│    ▼                                                                          │
│  qc/  ← package root, NO import streamlit anywhere in this subtree           │
│  ┌───────────────┐                                                            │
│  │ results.py    │  Rule (frozen dataclass) + register() — raises            │
│  │               │  ValueError("Duplicate rule id ...") at IMPORT TIME       │
│  │               │  if two layers register the same id. Declares canonical  │
│  │               │  order = (layer import order, then declaration order).   │
│  └───────┬───────┘                                                            │
│          │ every layer module registers its rule ids here at import time     │
│  ┌───────┴────┬────────────┬─────────────┬────────────┐                     │
│  │ schema.py  │  mlos.py   │settlement.py│ takeoff.py │ boundary.py         │
│  │  (S1,S2)   │(1-14,      │  (SQ1-SQ4)  │(TP2-TP5)   │  (B0-B3)            │
│  │            │ 11.*, 12.*)│             │            │                     │
│  └────────────┴────────────┴─────────────┴────────────┴─────────────────────┘
│  domain.py (constants) ◄──── referenced by all 5 layers + autocorrect.py     │
│  predicates.py (vec_is_uuid, vec_is_editor, pct) ◄── referenced likewise     │
│  autocorrect.py (auto_correct_mlos — moves, but its own defects stay out     │
│                  of scope per D-09)                                          │
└────────────────────────────────────────────────────────────────────────────────┘
            ▲
            │ verified by
tests/  test_results_registry.py       — duplicate-id rejection (ENGINE-01/02)
        test_no_streamlit_in_qc.py     — import-boundary guard (ENGINE-05)
        test_deterministic_order.py    — subprocess-pair byte-identical order (ENGINE-09)

requirements.txt  ← pandas==3.0.5, numpy declared+bounded, existing 3 bounded (ENGINE-07)
```

### Recommended Project Structure

```
qc/
├── __init__.py       # Claude's discretion (D from CONTEXT.md): re-export run_all() facade,
│                       # or leave callers to import each module directly
├── results.py         # Rule dataclass, register(), canonical-order registry
├── domain.py           # VALID_DAY, VALID_YN, VALID_YN_NA, VALID_ACC, VALID_HAB,
│                        # YN_NA_COLS (now a tuple), MLOS_REQUIRED_COLS,
│                        # TAKEOFF_REQUIRED_COLS, UUID_RE, EDITOR_RE
├── predicates.py        # vec_is_uuid, vec_is_editor, pct
├── schema.py             # run_schema_qc  (S1, S2)
├── mlos.py                # run_mlos_qc   (1-10, 11.urban/11.rural/11.scattered, 11a, 11b,
│                            #                12.highrisk...12.fulani, 13, 14)
├── settlement.py           # run_settlement_qc (SQ1-SQ4)
├── takeoff.py               # run_takeoff_qc (TP2-TP5)
├── boundary.py               # run_ward_boundary_qc (B0-B3)
└── autocorrect.py             # auto_correct_mlos (moves; logic untouched, D-09)

tests/
├── conftest.py            # minimal fixture DataFrames (not the full 3-format golden
│                            # fixture — that's Phase 2's ENGINE-06 scope)
├── test_results_registry.py
├── test_no_streamlit_in_qc.py
└── test_deterministic_order.py
```

Module names `domain.py`/`predicates.py` match `01-CONTEXT.md`'s suggestion and this repo's
snake_case single-word file convention (`codebase/CONVENTIONS.md`); the planner may rename them
— the only hard requirement is "lives under `qc/`, contains no `import streamlit`."

### Pattern 1: Import-Time Rule Registry (the seam)

**What:** A frozen `Rule` dataclass and a module-level `_REGISTRY: dict[str, Rule]` in
`qc/results.py`. Every rule id any layer will ever emit is registered via `register(id, layer,
name, description)` **at module import time** — not the first time a check runs — so a
duplicate is caught the instant `import qc` executes, independent of whether any DataFrame is
ever processed. This directly satisfies success criterion 2 ("Importing the rule registry with
a duplicated identifier fails immediately").

```python
# qc/results.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Rule:
    id: str            # e.g. "12.fulani" — globally unique
    layer: str          # "Schema" | "MLoS" | "Settlement" | "Takeoffpoint" | "Boundary"
    name: str
    description: str

_REGISTRY: dict[str, Rule] = {}
_ORDER: list[str] = []          # registration sequence == canonical emission order

def register(id: str, layer: str, name: str, description: str) -> Rule:
    if id in _REGISTRY:
        existing = _REGISTRY[id]
        raise ValueError(
            f"Duplicate rule id {id!r}: already registered for layer "
            f"{existing.layer!r} ({existing.name!r})"
        )
    rule = Rule(id, layer, name, description)
    _REGISTRY[id] = rule
    _ORDER.append(id)
    return rule

def canonical_order() -> list[str]:
    """Registration order == (layer import order, then declaration order within
    the layer) — matches CONTEXT.md's discretion note and the current display
    sequence Schema -> MLoS -> Settlement -> Takeoffpoint -> Boundary."""
    return list(_ORDER)
```

Each layer module declares its rule ids at the top of the file, at import time, e.g.:

```python
# qc/mlos.py  (excerpt — declared once, at import time, before run_mlos_qc is called)
from .results import register

register("1",  "MLoS", "Required Fields — Not Null", "...")
# ... 2 through 10 ...
register("11.urban",     "MLoS", "urban is Y or N",     "...")
register("11.rural",     "MLoS", "rural is Y or N",     "...")
register("11.scattered", "MLoS", "scattered is Y or N", "...")
register("11a", "MLoS", "Cannot be both Urban and Rural", "...")
register("11b", "MLoS", "Urban cannot be Scattered", "...")
register("12.highrisk",          "MLoS", "highrisk = Y/N/NA", "...")
register("12.slums",             "MLoS", "slums = Y/N/NA", "...")
register("12.densely_populated", "MLoS", "densely_populated = Y/N/NA", "...")
register("12.hard2reach",        "MLoS", "hard2reach = Y/N/NA", "...")
register("12.border",            "MLoS", "border = Y/N/NA", "...")
register("12.nomadic",            "MLoS", "nomadic = Y/N/NA", "...")
register("12.riverine",           "MLoS", "riverine = Y/N/NA", "...")
register("12.fulani",              "MLoS", "fulani = Y/N/NA", "...")
register("13", "MLoS", "Editor Format (firstname.surname)", "...")
register("14", "MLoS", "eha_guid is UUID", "...")
```

The eight `12.*` ids and their order come directly from D-01 in `01-CONTEXT.md`
`[VERIFIED: 01-CONTEXT.md:25]`; they are reproduced verbatim above, not re-derived.

**When to use:** Any rule set large enough that "does this id already exist?" is a live
question — true today at 27 ids with one documented collision class (F3), and explicitly
expected to grow to 35+ by Phase 7.

**Trade-off:** declaring every id twice (once in the registry block, once implicitly via the
`num` argument passed to the runtime `add()` helper) is mild duplication. It is the price of
catching a collision at import time rather than only the first time a specific code path
executes — worth paying once, now.

### Pattern 2: Deterministic Emission Order via Two Independent Mechanisms (D-10)

**What:** Order is enforced at both levels, per the locked decision:

1. **Immediate fix — ordered iterables.** `YN_NA_COLS` becomes a tuple in the exact order
   `01-CONTEXT.md` specifies: `("highrisk", "slums", "densely_populated", "hard2reach",
   "border", "nomadic", "riverine", "fulani")`. The R11 loop already iterates a list
   (`["urban", "rural", "scattered"]`, `app.py:927` `[VERIFIED: app.py:927-931]`) — already
   deterministic, no change needed there beyond the identifier itself.

   ```python
   # qc/mlos.py — R11 (identifier fix only; loop and logic unchanged)
   for col in ("urban", "rural", "scattered"):
       if col in mlos.columns:
           add(f"11.{col}", f"{col} is Y or N",
               f"{col} must be Y or N and must not be null",
               ~mlos[col].astype(str).str.strip().isin(VALID_YN), [col])

   # qc/mlos.py — R12 (identifier fix + YN_NA_COLS now a tuple, in domain.py)
   for col in YN_NA_COLS:
       if col in mlos.columns:
           add(f"12.{col}", f"{col} = Y/N/NA",
               f"{col} must be Y, N, or NA",
               ~mlos[col].astype(str).str.strip().isin(VALID_YN_NA), [col])
   ```

2. **Structural fix — registry-declared canonical order is the load-bearing half (D-12).** A
   tuple alone fixes today's symptom but does not stop a *future* contributor from introducing
   a new unordered iterable elsewhere. The registry's `canonical_order()` (registration
   sequence = layer import order, then declaration order within a layer — matching the current
   display sequence Schema → MLoS → Settlement → Takeoffpoint → Boundary, which also satisfies
   Phase 3's VERDICT-06 requirement that boundary checks read B0,B1,B2,B3) gives `qc/__init__.py`
   (or `app.py`) a way to **re-sort the final combined checks list by registered order** before
   returning it to the caller, regardless of what order any individual layer's runtime code
   happened to produce:

   ```python
   # qc/__init__.py (or wherever layer results are combined)
   from .results import canonical_order

   def _sort_by_registry(checks: list[dict]) -> list[dict]:
       order_index = {rule_id: i for i, rule_id in enumerate(canonical_order())}
       return sorted(checks, key=lambda c: order_index[c["Rule#"]])
   ```

   This is what makes a future regression (someone adding a new `set` literal in a new layer)
   fail a test rather than silently reappearing — the registry's declared order overrides
   whatever the runtime iteration produced, every time.

**Why not just sort `Rule#` lexicographically?** Flagged explicitly in `01-CONTEXT.md`'s
Claude's Discretion section: a naive lexicographic sort orders `1, 10, 11, 2` — worse than
today. Use registration/declaration order, never `sorted()` on the id string itself.

### Pattern 3: Cross-Process Determinism Is a Subprocess Test, Not a Same-Process Test

**What:** Python randomizes string hashing per process (`PYTHONHASHSEED`), which is exactly why
`YN_NA_COLS` as a `set` produced different iteration orders on different restarts. A test that
imports `qc` and calls `run_mlos_qc()` twice **in the same pytest process** cannot detect this
defect — the hash seed is fixed for the whole process. The standing test for ENGINE-09 must
spawn two actual subprocesses with different hash seeds and diff their output:

```python
# tests/test_deterministic_order.py
import subprocess, sys, json

_SNIPPET = """
import json
import qc
checks, _ = qc.mlos.run_mlos_qc(FIXTURE_MLOS_DF, FIXTURE_TAKEOFF_DF)
print(json.dumps([c["Rule#"] for c in checks]))
"""

def test_order_is_identical_across_hash_seeds():
    orders = []
    for seed in ("0", "1"):
        result = subprocess.run(
            [sys.executable, "-c", _SNIPPET],
            env={"PYTHONHASHSEED": seed, **os.environ},
            capture_output=True, text=True, check=True,
        )
        orders.append(json.loads(result.stdout))
    assert orders[0] == orders[1], (
        f"Rule emission order differs across process hash seeds: "
        f"{orders[0]!r} vs {orders[1]!r}"
    )
```

(The snippet needs a way to construct `FIXTURE_MLOS_DF`/`FIXTURE_TAKEOFF_DF` inline or via a
small pickled/CSV fixture the subprocess loads — mechanics are the planner's task-level detail;
the point that matters for planning is that **this test must fork a real subprocess with an
explicit differing `PYTHONHASHSEED`**, not just call the function twice in-process.) Before the
fix, running this exact pattern against the current `set`-based `YN_NA_COLS` at `app.py:100-101`
would show differing orders across seeds — the `01-CONTEXT.md` author already ran this
experiment directly ("confirmed by running the literal in three processes and getting three
different orders" — `01-CONTEXT.md`, Notes section of the phase description).

### Anti-Patterns to Avoid

- **Sorting the final `checks` list by `Rule#` string.** Produces `1, 10, 11, 2` ordering —
  actively worse than today. Use registration order (Pattern 2), never `sorted()` on the id.
- **Fixing F5 (non-deterministic `eha_guid` generation) while `auto_correct_mlos()` is being
  moved, because "it's right there."** D-09 explicitly accepts this as a deliberate tradeoff:
  the function moves now (so all pure code lands on the correct side of the seam in one move),
  but its two defects (F4 cache divergence, F5 non-deterministic GUIDs) are Phase 2 scope. Moving
  code and fixing its logic are different changes; conflating them here makes the diff harder to
  verify against "no changed verdicts."
- **A Great Expectations / soda-core / rule-DSL framework for ~35 rules in one repo.** Already
  rejected by this project's own `REQUIREMENTS.md` Out-of-Scope table and `ARCHITECTURE.md`'s
  Anti-Pattern 1 — the registry above borrows only the "identity is first-class and centrally
  validated" idea, not the machinery.
- **Testing determinism in-process.** A single pytest process has one fixed `PYTHONHASHSEED` for
  its entire run — calling `run_mlos_qc()` twice in the same test proves nothing about
  cross-restart stability (Pattern 3).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rule identity/uniqueness at scale | A custom YAML rule-config loader or a Great Expectations-style suite store | A ~30-line Python registry (Pattern 1) | This project has one team, one repo, ~35 rules — GE/soda's suite-store and DSL machinery solve "share rules across many pipelines/teams," not this problem (`ARCHITECTURE.md` Anti-Pattern 1, already researched for this project) |
| Streamlit-free import boundary detection | A custom import-hook or `sys.modules` inspector | `ast.walk()` over each `qc/*.py` file's parsed AST checking for `Import`/`ImportFrom` nodes naming `streamlit` (or the simpler `grep -rl streamlit qc/` MVP) | Both are five-to-fifteen-line, dependency-free, standard techniques; no need for import hooks or `sys.meta_path` machinery to answer "does this file import X" |
| Dependency reproducibility | A lockfile toolchain (`pip-tools`/`poetry`) introduced solely for this phase | Hand-pinned `requirements.txt` with explicit upper bounds | No build tooling exists in this repo today; a lockfile toolchain is a larger surface change than ENGINE-07 asks for (see Alternatives Considered) |
| UUID validity checking | A new custom UUID parser | Existing `vec_is_uuid()` (`app.py:210-212`, moves unchanged into `qc/predicates.py`) | Already vectorized, already correct, out of this phase's scope to touch (no changed verdicts) |

**Key insight:** every "don't hand-roll" item above is really the same lesson stated three
times — this phase's entire job is to add *one* small, well-scoped mechanism (a registry with an
import-time uniqueness check) and otherwise move code unchanged. Anything bigger than that is
solving a problem this phase does not have.

## Runtime State Inventory

Phase 1 renames 11 rule identifiers (the `11`/`12` duplicates) and relocates six functions —
this qualifies as a refactor/rename phase, so this section is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None.** No database exists yet (the append-only submission log is Phase 5's AUDIT-02 scope, not built). `st.session_state` caches `mlos_checks`/`mlos_detail`/etc. keyed by `(filename, size, takeoff_key)` (`app.py:1351-1361` `[VERIFIED: app.py:1351-1361]`), but this cache is process-memory-only and is wiped on every Space/process restart — it does not survive the deploy that ships this phase's rename, so there is no stale-identifier cache to migrate. | None. |
| Live service config | **None.** No external services (no HF Space yet — Phase 4; no SMTP config change in this phase; no n8n/Datadog-equivalent). | None. |
| OS-registered state | **None.** This is a Streamlit script with no OS-level task registration, no pm2/systemd/launchd unit. | None. |
| Secrets/env vars | **None.** Rule identifiers are not secrets and appear in no env var name; the `requirements.txt` pin change touches no secret. | None. |
| Build artifacts / installed packages | **None requiring action.** No `setup.py`/`pyproject.toml` packages this app as an installable distribution today, so there is no stale `.egg-info` directory analogous to the audited defect class. `__pycache__/` bytecode (already `.gitignore`d — confirmed by reading `.gitignore` in this session) is content-hashed by Python and will recompile cleanly against the moved code with no action needed. | None. |
| **Reports already filed by the data team** (not one of the five standard categories, but the closest analogue to "runtime state" this phase actually has) | Excel exports and emailed summaries already sent, citing `Rule 11`/`Rule 12` as single identifiers | **This is exactly why D-04 freezes the 27 non-duplicated identifiers exactly as-is** — no migration exists for a printed/emailed report, so the fix must be additive (new, more-specific ids for the 11 colliding checks) rather than a renumbering of everything. No code action beyond following D-01/D-04 as specified. |

**Canonical question answered:** after this phase's code changes ship, nothing outside the
codebase itself (no database, no external service, no OS registration, no secret) references the
old bare `"11"`/`"12"` identifiers in a way that requires migration — the only durable references
are historical documents (already-sent reports), which is precisely the constraint D-04 was
written to protect.

## Common Pitfalls

### Pitfall 1: Verdicts Silently Change During "Just a Move"

**What goes wrong:** Copy-pasting a 160-line function (`run_mlos_qc`, `app.py:805-965`) into a
new file is exactly the kind of edit where a stray character (a dropped `~`, a changed `.isin()`
to `.isna()`) silently flips a check's pass/fail result, and nobody notices because the phase's
own success criteria don't include a byte-for-byte behavior diff.
**Why it happens:** Six functions, hundreds of lines, moved in one phase, with no existing test
suite as a safety net (`TESTING.md`: "Framework: Not detected").
**How to avoid:** Before extracting, capture the `(checks, detail_df)` output of every layer
function against a small fixed fixture DataFrame (the domain's real column set, ~5-10 rows
exercising every rule). After extraction, re-run the same fixture through the new `qc/` package
and assert the two outputs match on every field **except** `Rule#` (which is expected to change
for the 11 renamed checks) — `Failing Rows`, `Total Rows`, `Status`, and the detail row contents
must be identical.
**Warning signs:** A `Failing Rows` count that changes for a rule whose identifier didn't change.

### Pitfall 2: In-Process Determinism Tests Prove Nothing

Covered in depth under Pattern 3 above — restated here because it is the single easiest mistake
to make when writing the ENGINE-09 standing test. A same-process test with two calls to
`run_mlos_qc()` will pass today and would have passed before the fix too, because
`PYTHONHASHSEED` is fixed once per process. Only a subprocess-spawning test with an explicit,
differing seed can distinguish "fixed" from "still broken."

### Pitfall 3: Sheet-Name Truncation Looks Risky But Isn't, Here

**What goes wrong (in general):** Excel sheet names truncate at 31 characters
(`f"Rule {rn}"[:31]`, confirmed at `app.py:1699, 1732, 1800` `[VERIFIED: app.py:1699]`), and
introducing longer, dotted identifiers could in principle cause two different rules to collide
on the same truncated sheet name.
**Why it's not a problem here:** The longest new identifier is `12.densely_populated` → `"Rule
12.densely_populated"` = 25 characters `[VERIFIED: character count performed in this session]`,
comfortably inside the 31-character limit, and no other new identifier is longer. This was
already checked in `01-CONTEXT.md` D-108's Integration Points section; this research confirms
the specific line numbers where the truncation happens and re-derives the count independently.
**Warning sign that would matter in a future phase:** Any new identifier longer than roughly 25
characters (leaving ~6 chars of headroom for the `"Rule "` prefix) should get an explicit
sheet-name-collision test before shipping.

### Pitfall 4: Re-Checking Pandas-3.0 Risk Patterns After the Files Move

**What goes wrong:** This session's `grep` for `dtype ==` / chained-assignment patterns
(`df[mask][col] = `) against the **current** `app.py` found zero hits — a genuinely clean
result. But that grep is only valid against the file as it exists *right now*; once code is
split into six new files under `qc/`, a stray edit made *during* the extraction (not before it)
would not be caught by a grep that was only run once, before the move.
**How to avoid:** Re-run the same two greps (`dtype ==` comparisons, `\]\[.*\] = ` chained
assignment) against every file under `qc/` as a verification step at the end of the extraction
task, not just as pre-work.

### Pitfall 5: `qc/__init__.py` Importing Back Into Itself

**What goes wrong:** If `qc/__init__.py` re-exports a `run_all()` facade that imports all five
layer modules, and any layer module (e.g. `mlos.py`) imports something from `qc/__init__.py`
(even indirectly, via `from qc import domain` triggering `__init__.py`'s own top-level imports),
Python's circular-import resolution can produce a partially-initialized module error that is
confusing to debug and highly sensitive to import order.
**How to avoid:** Layer modules should import directly from sibling modules (`from
.domain import VALID_YN`, `from .results import register`), never from the package's own
`__init__.py`. `__init__.py` is the only file allowed to import from all the others.

## Code Examples

### Duplicate-id rejection test (ENGINE-02's standing test)

```python
# tests/test_results_registry.py
import importlib
import pytest

def test_duplicate_rule_id_raises_at_registration():
    from qc.results import register
    register("__test_dup__", "Test", "first", "...")
    with pytest.raises(ValueError, match="Duplicate rule id"):
        register("__test_dup__", "Test", "second", "...")

def test_current_ruleset_has_no_duplicates():
    """Regression guard: importing the real qc package must not raise, and
    every id declared across all five layers must be unique."""
    import qc  # importing the real package triggers every register() call
    from qc.results import canonical_order
    ids = canonical_order()
    assert len(ids) == len(set(ids)), f"Duplicate ids found: {ids}"
```

### No-streamlit-import guard test (ENGINE-05)

```python
# tests/test_no_streamlit_in_qc.py
import ast
from pathlib import Path

QC_DIR = Path(__file__).parent.parent / "qc"

def test_no_module_under_qc_imports_streamlit():
    offenders = []
    for path in QC_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] == "streamlit" for alias in node.names):
                    offenders.append(str(path))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] == "streamlit":
                    offenders.append(str(path))
    assert not offenders, f"streamlit imported in: {offenders}"
```

### `requirements.txt` — final pinned form

```
streamlit>=1.32.0,<2.0.0
pandas==3.0.5
numpy>=2.0.0,<3.0.0
openpyxl>=3.1.0,<4.0.0
xlrd>=2.0.1,<3.0.0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `add()` closure copy-pasted verbatim in 5 functions, keying results to a bare `"Rule#"` string | Single shared registry (`qc/results.py`) with an import-time uniqueness guard | This phase | Duplicate ids become structurally impossible to reintroduce silently, not just discouraged by convention |
| `YN_NA_COLS` as a `set` literal | `YN_NA_COLS` as a `tuple`, plus registry-declared canonical order as the structural backstop | This phase | Emission order stops depending on Python's per-process string-hash randomization |
| `pandas>=2.0.0` unbounded | `pandas==3.0.5` exact pin | This phase | Every subsequent phase is tested against one known pandas version instead of "whatever resolved that day" |

**Deprecated/outdated:** Nothing in this phase deprecates a previously-supported approach —
this is additive structural work, not a migration away from a prior public API.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ENGINE-07's upper-bound requirement extends to `streamlit`/`openpyxl`/`xlrd`, not only the two packages the requirement text names explicitly (`pandas`, `numpy`) | Standard Stack | If the planner reads ENGINE-07 narrowly (pandas + numpy only), three dependencies stay unbounded and the exact same "silent drift" failure mode ENGINE-07 exists to close remains open for streamlit/openpyxl/xlrd. Low-cost to resolve either way — confirm the reading with the user or default to the broader (safer) interpretation. |
| A2 | `pytest` (rather than `unittest` or another framework) is the right choice for this phase's test infrastructure | Standard Stack / Validation Architecture | Low risk — `pytest` is already what this project's own `codebase/TESTING.md` recommended in its "Recommended Testing Approach" section, and it is already installed in this dev environment. Switching later would mean rewriting a small number of new test files, not a large migration. |
| A3 | Test dependencies (`pytest`) should live in a separate `requirements-dev.txt` rather than directly in `requirements.txt` | Standard Stack, Alternatives Considered | Low risk either way — if the planner prefers one file, the only cost is a slightly heavier production install on the eventual HF Space (installing `pytest` there is harmless, just unnecessary). |

## Open Questions

1. **Should this phase also pin a Python version floor (e.g., a `.python-version` file or a
   `requirements.txt` comment), given `pandas==3.0.5` requires Python `>=3.11`?**
   - What we know: no Python version is pinned anywhere in this repo today (no `runtime.txt`, no
     `pyproject.toml` `requires-python`); the local dev environment used for this research runs
     Python 3.13.1, comfortably satisfying the floor.
   - What's unclear: whether declaring a Python floor is this phase's responsibility (it directly
     enables the pandas pin to resolve correctly) or Phase 4's (which is where the HF Space's
     actual deployment `python_version:` README field gets set, per `STACK.md`).
   - Recommendation: at minimum, add a one-line comment in `requirements.txt` noting the Python
     `>=3.11` floor pandas 3.0.5 requires, so the constraint is discoverable before Phase 4 rather
     than surfacing as a deploy-time resolution failure with no obvious cause.

2. **Exact wording/placement of the `ValueError` message for a duplicate rule id.**
   - What we know: success criterion 2 requires the message to name the collision.
   - What's unclear: whether the message format shown in this research (naming both the new id,
     the existing layer, and the existing rule name) is sufficient, or whether the planner wants
     a more structured error (e.g., a custom `DuplicateRuleError` exception class rather than a
     bare `ValueError`).
   - Recommendation: a bare `ValueError` with a descriptive message satisfies the literal success
     criterion; a custom exception class is a reasonable planner preference but not required.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | entire app | ✓ | 3.13.1 (local dev) `[VERIFIED: python3 --version]` | — |
| pandas | QC engine | ✓ (needs bump) | 3.0.2 installed, 3.0.5 required | `pip install pandas==3.0.5` |
| numpy | SQ4 haversine | ✓ | 2.4.4 installed, `<3.0.0` floor satisfied | — |
| pytest | new test suite | ✓ | 9.0.3 installed locally `[VERIFIED: python3 -m pytest --version]` | — |
| streamlit | app.py (not `qc/`, by design) | **Not installed in this dev environment** `[VERIFIED: import streamlit raised ModuleNotFoundError in this session]` | — (latest on PyPI: 1.63.0) | This is actually favorable: success criterion 3 ("`import qc` succeeds in an interpreter with Streamlit uninstalled") can be verified directly in this exact environment without any special isolation setup. |
| git | version control | ✓ (repo already initialized) | — | — |

**Missing dependencies with no fallback:** none — `streamlit`'s absence in the dev environment is
a positive signal for this phase, not a blocker (app.py itself is not the code under test here).

**Missing dependencies with fallback:** none beyond the version bumps listed above, which have no
fallback need (a `pip install` resolves them directly).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` — none currently installed as a project dependency; available at `9.0.3` in this session's dev environment |
| Config file | none — create in Wave 0 (a minimal `pytest.ini` or `[tool.pytest.ini_options]` in a new `pyproject.toml`, planner's choice) |
| Quick run command | `pytest tests/ -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| ENGINE-01 | Every check id is unique across all layers | unit | `pytest tests/test_results_registry.py::test_current_ruleset_has_no_duplicates -x` | ❌ Wave 0 |
| ENGINE-02 | Registering a duplicate id raises immediately, at import time | unit | `pytest tests/test_results_registry.py::test_duplicate_rule_id_raises_at_registration -x` | ❌ Wave 0 |
| ENGINE-05 | No module under `qc/` imports streamlit | unit (AST-based) | `pytest tests/test_no_streamlit_in_qc.py -x` | ❌ Wave 0 |
| ENGINE-07 | `pip install -r requirements.txt` resolves `pandas==3.0.5`, `numpy` declared+bounded | smoke (environment, not application logic) | `pip install -r requirements.txt && python -c "import pandas; assert pandas.__version__ == '3.0.5'"` | ❌ Wave 0 (not a pytest test — a CI/install-time assertion) |
| ENGINE-09 | Two separate processes emit checks in byte-identical order | integration (subprocess-spawning) | `pytest tests/test_deterministic_order.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x` (fast — no golden-fixture 3-format harness exists yet;
  that is Phase 2's ENGINE-06 scope, not this phase's)
- **Per wave merge:** `pytest tests/` (full suite — still small at this phase's scope)
- **Phase gate:** Full suite green, plus the `pip install` smoke check for ENGINE-07, before
  `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `pytest` added to the dependency set (`requirements.txt` directly or a new
      `requirements-dev.txt` — see Assumptions Log A3)
- [ ] `tests/` directory created — does not exist anywhere in this repo today
      `[VERIFIED: find in this session found no test files]`
- [ ] `tests/conftest.py` — minimal fixture DataFrame(s) sufficient to exercise every rule id
      (not the full 3-format golden fixture set — that is Phase 2's ENGINE-06 responsibility)
- [ ] `tests/test_results_registry.py`, `tests/test_no_streamlit_in_qc.py`,
      `tests/test_deterministic_order.py` — all three net-new
- [ ] A pytest config file (`pytest.ini` or `pyproject.toml`) — none exists; needed so `pytest`
      discovers `tests/` without extra CLI flags

## Security Domain

This phase is a pure internal refactor with no new external interface, no new user input path,
and (per the phase's own scope statement in `01-CONTEXT.md`) no changed verdicts — so most ASVS
categories are not applicable. The two that are relevant are both about *architecture*, which is
exactly what this phase changes.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V1 Architecture, Design and Threat Modeling | Yes | The `qc/` package's no-`import streamlit` boundary *is* an architectural trust-boundary control — it guarantees a bug or future change inside the QC engine cannot reach session state, network I/O, or any Streamlit-mediated capability. Enforced by the AST-based guard test (ENGINE-05), not by convention. |
| V5 Input Validation | Applies, unchanged | The moved functions (`run_*_qc`, `auto_correct_mlos`) are the app's existing input-validation logic, processing externally-supplied file content. This phase relocates but explicitly must not alter this logic (D-09, phase scope statement: "no new checks and no changed verdicts") — validation posture is frozen by design, not newly introduced here. |
| V2 Authentication | No | Out of scope — Phase 4 |
| V3 Session Management | No | Out of scope — Phase 4 introduces auth; this phase's `st.session_state` usage is unchanged |
| V4 Access Control | No | Out of scope — no access-control concept exists in the app yet |
| V6 Cryptography | No | `uuid.uuid4()` in `auto_correct_mlos()` generates a data-field identifier, not a security token; unchanged by this phase and not security-sensitive in this context |

### Known Threat Patterns for This Phase's Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| A future change accidentally introduces a Streamlit (or other UI-layer) dependency into `qc/`, eroding the "pure, testable engine" boundary | Tampering (of the trust boundary itself) | AST-based import guard test (ENGINE-05), run on every commit — not a one-time manual review |
| A future rule addition reintroduces a `set`-literal iteration, silently reopening the non-deterministic-order defect | Tampering (of report integrity — two runs over the same data producing different reports) | The registry's `canonical_order()` re-sort (Pattern 2) makes final emission order a property of the static registry, not of whatever iteration a new rule's code happens to use; the subprocess-based standing test (ENGINE-09) catches a regression even if the re-sort is somehow bypassed |

## Sources

### Primary (HIGH confidence)
- Direct reads of `app.py` in this session — line ranges cited inline throughout this document
  (`:100-101`, `:210-230`, `:232-296`, `:383-536`, `:539-633`, `:695-1012`, `:1015-1154`,
  `:1172-1430`, `:1643-1800`)
- `python3 -m pip index versions <pkg>` — run live against PyPI in this session for `pandas`,
  `numpy`, `streamlit`, `openpyxl`, `xlrd`, `pytest`
- `01-CONTEXT.md` — locked user decisions (D-01 through D-12), reproduced verbatim where quoted
- `.gitignore`, `requirements.txt`, `.planning/config.json` — read directly in this session

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md`, `.planning/research/STACK.md` — this project's own prior
  research, itself HIGH-confidence per its own sourcing (official Streamlit/pandas/geopandas docs
  via Context7, PyPI-verified versions), produced the same day as this research
- `.planning/codebase/TESTING.md`, `.planning/codebase/CONCERNS.md`,
  `.planning/codebase/CONVENTIONS.md` — this project's own codebase-mapping research

### Tertiary (LOW confidence)
- `gsd_run query package-legitimacy check` output for pandas/numpy/pytest — all three verdicts
  assessed in this document as heuristic false positives (see Package Legitimacy Audit); flagged
  as LOW confidence in isolation, corroborated to HIGH confidence by the independent PyPI version
  checks and by pandas/numpy/pytest's well-established public identity

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version number directly verified against live PyPI in this
  session, not training data
- Architecture: HIGH — the registry pattern is a direct, narrowed application of this project's
  own prior `ARCHITECTURE.md` research (Pattern 1), plus direct code reads confirming every line
  anchor cited
- Pitfalls: HIGH — the pandas-3.0 risk patterns (dtype comparisons, chained assignment) were
  specifically grepped-for in this session and confirmed absent from the current codebase, not
  assumed absent

**Research date:** 2026-09-09
**Valid until:** 2026-10-09 (30 days — stable domain: no fast-moving external API surface, but
PyPI version numbers should be re-verified if planning is delayed past this window)
