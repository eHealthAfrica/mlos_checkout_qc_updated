# Phase 2: Detection Correctness and Three-Format Harness - Research

**Researched:** 2026-09-10
**Domain:** pandas data-integrity rules, Streamlit session-state caching, SQLite/CSV/XLSX round-tripping, pytest fixture/baseline design
**Confidence:** HIGH (every claim below is either read directly from this repo's code/tests this session, or empirically verified by running code against the project's own pinned `.venv` — pandas 3.0.5, streamlit 1.63.0, pytest 9.1.1)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Absence Predicate (INTEG-01, shared with INTEG-02)**
- D-04: A value is absent when it is pandas NA/None/NaN, empty string, whitespace-only, or one of the case-insensitive sentinels `null`, `none`, `n/a`, `nan`, `-`. Single predicate shared by Rule 1 and the cross-table rules. The narrower three-state predicate was recommended and NOT chosen — the sentinel list is deliberate and must not be quietly narrowed.
- D-05: Sentinel list applies uniformly to every column, with exact literal `"NA"` exempted case-sensitively (restricting sentinel matching to flag columns/state_code only was recommended and NOT chosen). Consequence: `highrisk = "N/A"` now reads as absent rather than reaching Rule 12. Required guard: the sentinel list + `"NA"` exemption must be a named, version-controlled constant in `qc/domain.py`, with a standing test asserting `"NA"` survives as present in every flag column and as `state_code`, and lowercase `"na"` is not swept up.

**Blank-Side Cross-Table Matches (INTEG-02)**
- D-01: A blank becomes its own registered finding, separate from a failed match. Six new checks distinguish "nothing to match on" from "no match found."
- D-02: The six identifiers are `2.missing`, `3.missing`, `4.missing`, `TP2.missing`, `TP3.missing`, `TP4.missing`. Reversibility: costly.
- D-06: Each `.missing` finding reports blanks in its own subject table only.
- D-07: `2.missing`, `3.missing`, `4.missing` emit unconditionally, including when no Takeoffpoint table was supplied. The Takeoffpoint-side trio still runs only when that table exists.
- D-03: Layers report overlap independently. A blank `ward_code` fires Rule 1, `4.missing` and B0 — three failing checks for one cell, and that is correct. Suppressing duplicates would couple layers.

**Column Normalisation (INTEG-03)**
- D-08: Normalisation is purely typographic: trim, lowercase, whitespace/hyphen runs to underscore, collapse repeated underscores. No semantic aliasing.
- D-20 (user directive): `README.md` is the canonical column vocabulary — its 43+4 required-column tables. Verified during discussion to match `qc/domain.py` exactly, zero drift. A future divergence is a defect.
- D-09: Every header is renamed to its normalised form, no canonical-set membership test — `Field Notes` becomes `field_notes` even though no rule reads it.
- D-10: When two headers normalise to the same label, a new registered Schema-layer check `S3` "Column Name Collision" fails, naming both original headers, and that colliding pair is left un-normalised so no duplicate label is ever created. S1 reports it missing; every other rule runs normally.
- D-11: Renames reported in two places: an on-screen expander (headers that actually changed) and a "Columns Renamed" sheet in the downloadable report. No Pass/Fail, no score weight.

**One Snapshot and Generated Identifiers (ENGINE-03, ENGINE-04)**
- D-12: `eha_guid` is a `uuid4()` computed once per submission and cached, reused for every render and download. Deterministic content-derived UUIDv5 was recommended and NOT chosen. Accepted consequence: IDs stable within a session but not across sessions/restarts.
- D-13: Submission identity is a sha256 over the uploaded bytes (both files when a separate Takeoffpoint is supplied), replacing `(uploaded.name, size, tp_key)` at `app.py:693` and its reuse as `qc_cache_key` at `app.py:722`.
- D-14: Session state holds both frames under distinct keys — `mlos_raw` as uploaded and `mlos_corrected` after auto-correction. On-screen table, all five QC layers and the auto-corrected download always read `mlos_corrected`; only the report's as-submitted sheet reads `mlos_raw`. Accepted cost: two frames coexist; peak memory for the frame is stated as "doubles" in CONTEXT.md (established fact #3 below shows this is pessimistic under CoW).
- D-15: Structural guard — distinct names, no bare `mlos_df` surviving, plus a standing AST test asserting all five `run_*_qc` calls / the on-screen table / `build_corrected_excel` receive `mlos_corrected`, and `mlos_raw` appears at exactly one call site. A `qc.run_all()` façade was offered and NOT chosen — Phase 1's declination (`qc/__init__.py:10`) stands.
- The second `auto_correct_mlos` call at `app.py:982` is deleted, reading the cached corrected frame instead.

**Boundary Reference Fallback (INTEG-04)**
- D-16: New registered `B4` "Boundary Reference Fallback" fails whenever the widening fired; description must name B2 as well as B1 (the fallback reassigns `filtered_bbox` too). B1 keeps running.
- D-17: B4 emits on every run where a reference exists — PASS or FAIL.
- D-18: Separate `B5` "Boundary Reference Unavailable" reports a missing reference — with no reference, `load_boundary_refs` returns empty frames and B1/B2/B3 all silently fail to emit; only B0 runs.
- D-19: In that same run, B4 emits nothing (no scope for B4 to describe). B5 carries the whole story.
- Canonical boundary order becomes B0, B1, B2, B3, B4, B5 (satisfies Phase 3's VERDICT-06).

### Claude's Discretion
- Which load paths normalisation covers (MLoS + both Takeoffpoint paths clearly need it; the two bundled boundary reference CSVs are defensive-only) — must be the same single helper wherever applied.
- `Failing Rows`/`Total Rows` for S3, B4, B5 — run-level conditions, follow S1/S2's non-row-denominator precedent.
- Where the absence predicate lives — `qc/predicates.py` for `vec_is_absent`, sentinel constant in `qc/domain.py`.
- Golden fixture construction (ENGINE-06) — strong recommendation to round-trip through the real loaders; two open choices (write-to-disk vs. in-memory, and comparison strictness) are this research's primary subject (see Architecture Patterns below).
- `_NOT_NULL_COLS` membership is not up for revision.

### Deferred Ideas (OUT OF SCOPE)
- Nearest non-matching candidate on cross-table mismatch detail rows (fuzzy-matching reconciliation aid) — its own phase.
- Known-alias column map (`wardcd` → `ward_code`, etc.) — rejected, infers intent from a name.
- Content-derived `eha_guid` (UUIDv5) — not chosen; revisit alongside v2's HIST-01.
- Telling the officer generated `eha_guid` values are session-scoped — raised, not taken up.
- B2's unmatched-bounding-box silent pass (`in_reference = merged["min_lon"].notna()`, `qc/boundary.py:155`) — belongs with Phase 7's GEO-01/GEO-03.
- Missing-boundary-reference scoring (making B5 not score as a pass) — Phase 3's VERDICT-05.
- `qc.run_all()` façade — declined, consistent with Phase 1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTEG-01 | Rule 1 flags missing required fields identically across `.sqlite`/`.csv`/`.xlsx` | Established Fact 1 (root cause confirmed); `vec_is_absent` design in Architecture Patterns; Code Example 1 |
| INTEG-02 | A blank value cannot satisfy a cross-table match rule (R2/R3/R4/TP2/TP3/TP4) | D-01/D-02/D-03 mask-design finding in Architecture Patterns (Pattern 2) — the "exactly three checks" derivation |
| INTEG-03 | Column names normalised once at load; renames reported | Established Fact 2 (rename-collision crash); Pattern 3 (collision-before-rename) |
| INTEG-04 | Boundary reference fallback surfaces as a visible warning | B4/B5 emission-condition analysis in Priority 3 / Pitfall 4 |
| ENGINE-03 | Displayed data and computed checks always describe the same submission version | D-14/D-15 AST-guard design in Pattern 4; three session-state keys identified (not one) |
| ENGINE-04 | Auto-correction runs exactly once per submission | Pattern 4; deletion of `app.py:982`'s second call |
| ENGINE-06 | pytest suite + three-format golden fixture | Priority 1 — Pattern 1, empirically verified this session |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Absence predicate (`vec_is_absent`) | API/Backend (`qc/predicates.py`) | — | Pure vectorised pandas function, no UI or storage concerns; consumed by every QC layer |
| Sentinel/NA vocabulary constant | API/Backend (`qc/domain.py`) | — | Domain vocabulary, not presentation |
| Column normalisation + collision detection | API/Backend (new `qc/` module or existing `qc/schema.py`) | Frontend Server (App.py renders the rename report) | Normalisation logic is pure; the on-screen expander and "Columns Renamed" sheet are presentation of its output |
| Cross-table `.missing` checks (2/3/4/TP2-4.missing) | API/Backend (`qc/mlos.py`, `qc/takeoff.py`) | — | Same shape as existing R2-4/TP2-4, lives beside them |
| Boundary fallback checks (B4, B5) | API/Backend (`qc/boundary.py`) | — | Rides existing `run_ward_boundary_qc` return value; no new consumer plumbing |
| Submission identity (sha256) | Frontend Server (`app.py`, `st.session_state`) | — | Reads `UploadedFile.getvalue()`, a Streamlit-runtime object; `qc/` must stay Streamlit-free (ENGINE-05) |
| `mlos_raw`/`mlos_corrected` snapshot cache | Frontend Server (`app.py`, `st.session_state`) | — | Session-scoped caching is a Streamlit concern; `auto_correct_mlos` itself (the pure transform) stays in `qc/` |
| Golden three-format fixture harness | Test/Dev tooling (`tests/`) | — | Exercises the real `app.py` loader functions, but the harness itself is test infrastructure, not shipped code |

## Summary

This phase's seven requirements decompose into two kinds of work: five deterministic, mechanical
fixes to `qc/` modules (absence predicate, `.missing` checks, column normalisation, B4/B5), and
two session-lifecycle fixes to `app.py`'s `st.session_state` usage (one-snapshot, sha256 identity).
None of it requires a new external dependency — `hashlib`, `re`, `sqlite3`, `io.BytesIO` are all
stdlib, and `pandas`/`streamlit`/`openpyxl` are already pinned. The **Package Legitimacy Audit**
section below is therefore empty by design.

The highest-risk part of this phase is not the rule logic — it is the interaction with Phase 1's
test scaffolding. `tests/baseline/qc_baseline.json` is a **frozen, pre-fix snapshot**; Phase 2
deliberately changes check counts (`S3`, `B4`, `B5` are new registrations; `2.missing` etc. are new
registrations), so every one of `tests/test_extraction_parity.py`'s five per-layer tests **will
fail on a bare length mismatch** the moment these land, regardless of whether the detection logic
itself is correct. This is not a regression to fix by patching the baseline — `qc_baseline.json`
and `capture_baseline.py`'s own docstrings forbid regeneration, because they exist to preserve the
numeric record of Phase 1's F3 defect (see Priority 2 below for the concrete disposition).

The second highest-risk item is silent scope creep in the absence-predicate fix: D-03 states a
blank `ward_code` fires **exactly three** checks (Rule 1, `4.missing`, B0) — not four. This means
Rule 4's own match-mask must **exclude** absent source cells, not merely rely on `""` no longer
being in the valid target set. This is a specific, derivable implementation requirement that is
easy to get wrong by only "fixing the valid-set construction" and stopping there.

**Primary recommendation:** implement `vec_is_absent` and the sentinel constant first (it is a
pure function with no dependents yet), verify it against the standing-test requirement from D-05,
then thread it through Rule 1, the six `.missing` checks (with the mask-exclusion fix above), the
column-normalisation collision detector, and finally the session-state identity/snapshot changes
in `app.py` — in that order, because each later piece can be tested against the earlier ones
using the existing fixture builders once those builders are extended (see Priority 2).

## Established Facts (carried in from the orchestrator's prior empirical verification — do not re-derive)

These four facts were verified by running code in this repo against pandas 3.0.5 before this
research pass began, and are restated here in full so the planner has them in one place alongside
this document's own findings.

1. **INTEG-01 / F2 root cause, confirmed.** With `dtype=str, keep_default_na=False`:
   - `pd.read_csv` empty cell  -> `''`   (dtype `str`), `.isna()` = **False**
   - `ExcelFile.parse` empty   -> `''`   (dtype `str`), `.isna()` = **False**
   - `pd.read_sql_query` NULL  -> `NaN`  (dtype `str`), `.isna()` = **True**
   Rule 1's `mlos[_NOT_NULL_COLS].isnull().any(axis=1)` (`qc/mlos.py:92`) therefore detects
   missing values ONLY for `.sqlite` uploads. `'   '` and `'NA'` are `.isna()` = False in all
   three. This asymmetry IS the defect.

2. **`DataFrame.rename` does NOT raise on a colliding target.** Renaming both `Ward Code` and
   `ward_code` to `ward_code` silently yields duplicate column labels; `df["ward_code"]` then
   returns a **DataFrame**, and `.astype(str).str.strip()` raises `AttributeError: 'DataFrame'
   object has no attribute 'str'`. **Consequence for D-10: collision detection MUST happen
   BEFORE the rename is applied, not after.**

3. **Copy-on-Write is always enabled in pandas >= 3.0 and cannot be disabled** (setting
   `mode.copy_on_write` is deprecated and a no-op). `df = src.copy()` followed by
   `df.loc[mask, col] = value` works correctly and leaves `src` untouched — so the five
   corrections in `qc/autocorrect.py` are safe as written. Under CoW, unmodified columns are
   shared between `mlos_raw` and `mlos_corrected`, so **D-14's two-frame model costs far less
   memory than "doubling"** — only corrected columns are copied. 02-CONTEXT.md's memory note
   is pessimistic; say so in the plan.

4. **The D-04/D-05 absence predicate behaves as specified** on a `str`-dtype Series:
   `s.isna() | t.eq("") | (t.str.lower().isin(SENTINELS) & ~t.eq("NA"))` where
   `t = s.astype(str).str.strip()` and `SENTINELS = {"null","none","n/a","nan","-"}`.
   Verified: `None`, `''`, `'  '`, `'N/A'`, `'nan'`, `'-'` -> absent; `'NA'`, `'na'`, `'N'`,
   `'0'`, `'Gidan Ali'` -> present. Note `'na'` (lowercase) stays PRESENT because it is not a
   sentinel — consistent with D-05's exact case-sensitive `"NA"` exemption.

   *(Correction from this session's re-read of `qc/domain.py`: `FLAG_COLS` — the correction
   target for auto-correct's NULL→"NA" fix — does not include `state_code`; the fact that `"NA"`
   is also Nasarawa's `state_code` is a separate reason the exemption must be global, not
   per-column. Both reasons point to the same design, D-05's uniform sentinel list.)*

## Standard Stack

No new external dependency is required. Every capability in this phase is built from packages
already pinned in `requirements.txt` (verified `[VERIFIED: requirements.txt, read this session]`):

| Library | Version (pinned) | Purpose in this phase |
|---------|---------|---------|
| `pandas` | `==3.0.5` | Vectorised absence predicate, column renaming, all rule masks |
| stdlib `hashlib` | n/a (stdlib) | sha256 over uploaded bytes (D-13) |
| stdlib `re` | n/a (stdlib) | Column-name normalisation (trim/lowercase/whitespace-hyphen collapse) |
| stdlib `ast` | n/a (stdlib) | D-15's structural standing test (Phase 1 precedent: `test_no_streamlit_in_qc.py`, `capture_baseline.py`) |
| stdlib `sqlite3` | n/a (stdlib) | Golden-fixture `.sqlite` construction (`CREATE VIEW`) |
| `openpyxl` | `>=3.1.0,<4.0.0` | Golden-fixture `.xlsx` construction via `pd.ExcelWriter` |
| `pytest` | `>=8.0.0,<10.0.0` (installed: 9.1.1) `[VERIFIED: .venv/bin/python -m pytest --version, run this session]` | Test harness |

No installation step is required; `requirements.txt` needs no edits for this phase.

## Package Legitimacy Audit

**Not applicable — this phase introduces no new external packages.** All logic is built from
packages already pinned and installed (`pandas`, `openpyxl`, stdlib `hashlib`/`re`/`ast`/`sqlite3`).
No `npm view` / `pip index versions` / registry check is needed, and no `checkpoint:human-verify`
gate is required for dependency installation in this phase's plan.

## Architecture Patterns

### System Architecture Diagram

```
Officer's browser
      │  uploads file(s)
      ▼
app.py: get_uploaded_data(uploaded_file)
      │  1. content_hash = sha256(uploaded_file.getvalue())        <- D-13 (new)
      │  2. cache check: session_state["uploaded_cache_key"] == content_hash?
      │       hit  → return cached mlos_raw / takeoff_df
      │       miss → dispatch by extension:
      │              .sqlite/.db → load_sqlite() → load_view() x2 (named views)
      │              .csv        → load_csv()
      │              .xlsx/.xls  → load_xlsx() (sheet-alias resolution)
      ▼
qc/columns.py (new): normalize_columns(df)          <- INTEG-03 (D-08/D-09/D-10)
      │  - detect same-normalised-name collisions BEFORE renaming (Est. Fact 2)
      │  - rename everything else; return (renamed_df, renames_applied, collisions)
      ▼
app.py: session_state["mlos_raw"] = normalized frame               <- D-14
      │
      ▼
qc/autocorrect.py: auto_correct_mlos(mlos_raw)  -- runs EXACTLY ONCE per content_hash
      │  uuid4() cached alongside content_hash, not regenerated     <- D-12
      ▼
app.py: session_state["mlos_corrected"] = corrected frame           <- D-14
      │
      ├──────────────┬──────────────┬───────────────┬───────────────┐
      ▼              ▼              ▼               ▼               ▼
qc/schema.py    qc/mlos.py     qc/settlement.py  qc/takeoff.py  qc/boundary.py
(S1,S2,S3)    (1,2,2.missing,   (SQ1-SQ4)      (TP2,TP2.missing, (B0-B5)
              3,3.missing,                      TP3,TP3.missing,
              4,4.missing,                      TP4,TP4.missing,
              5-14)                             TP5)
      │              │              │               │               │
      └──────────────┴──────────────┴───────────────┴───────────────┘
                                     ▼
                    qc.sort_by_registry(checks)  -- canonical order B0..B5 etc.
                                     ▼
                    on-screen tables / Excel report / email summary
                    (all read session_state["mlos_corrected"], EXCEPT
                     the report's as-submitted sheet, which reads
                     session_state["mlos_raw"])                     <- D-14/D-15
```

### Pattern 1: Three-Format Golden Fixture (ENGINE-06)

**Core design insight, empirically verified this session:** the three exports must NOT be
byte-identical representations of the same DataFrame — they must be the same **logical** dataset,
each written through the format's own natural blank-cell convention. A `.sqlite` export of a truly
missing value is a SQL `NULL` (`cursor.execute(..., (None, ...))`); a `.csv`/`.xlsx` export of the
same logical gap is an empty string cell. If the fixture instead wrote `""` into the sqlite table
too, the golden test could never reproduce INTEG-01, because the whole defect is that
`pd.read_sql_query` turns SQL `NULL` into `NaN` (which `.isnull()` catches) while
`pd.read_csv`/`ExcelFile.parse` under `keep_default_na=False` turn a blank cell into `""` (which
`.isnull()` does not catch) — see Established Fact 1. **The fixture builder must therefore accept
a per-row "logical blank" marker and translate it differently per format**, not write one common
representation.

**Verified this session** (`.venv/bin/python3`, pandas 3.0.5, streamlit 1.63.0) — every mechanical
piece of the round-trip works exactly as `app.py`'s functions expect:

1. `PRAGMA table_info("<view_name>")` works identically against a `CREATE VIEW ... AS SELECT * FROM <table>` as it does against a real table — confirmed by creating
   `master_list_settlement_update_view`/`mlos_takeoffpoint_view` as views over plain tables and
   running `load_view()` verbatim against them. `[VERIFIED: empirical test, this session]`
2. A minimal `io.BytesIO` subclass carrying only `.name` and `.size` attributes (no other
   Streamlit machinery) passes through **all three** of `get_uploaded_data`'s branches unmodified:
   `pd.read_csv(file_like, ...)`, `pd.ExcelFile(file_like)`, and `load_sqlite`'s
   `tmp.write(uploaded_file.read())` tempfile path. `[VERIFIED: empirical test, this session]`
3. Streamlit's real `UploadedFile` class (`streamlit.runtime.uploaded_file_manager.UploadedFile`)
   **is itself** a subclass of `io.BytesIO` — confirmed by reading the installed package source
   this session — so a fixture that uses a bare `io.BytesIO`-with-`.name` stand-in is testing the
   same code path the real object would exercise, not a divergent shim.
   `[VERIFIED: .venv/lib .../streamlit/runtime/uploaded_file_manager.py, read this session]`
4. `.getvalue()` exists on both the real `UploadedFile` and a plain `io.BytesIO`, and — confirmed
   by checking `.tell()` immediately after calling it — does **not** move the read position.
   Streamlit's own docstring for `UploadedFile` states this explicitly: *"After you read the file
   to the end, another `read()` returns no data. Use `getvalue()` to read the full contents
   without changing the position, or `seek(0)` to rewind."*
   `[VERIFIED: .venv/lib .../streamlit/runtime/uploaded_file_manager.py docstring, read this session]`

**Recommended fixture shape** (extends the existing `tests/fixtures.py` pattern rather than
replacing it):

```python
# tests/golden_fixture.py (new) — or a new section of tests/fixtures.py
import io, sqlite3, tempfile, os
import pandas as pd

MLOS_VIEW = "master_list_settlement_update_view"
TAKEOFF_VIEW = "mlos_takeoffpoint_view"

class FakeUploadedFile(io.BytesIO):
    """Minimal stand-in for streamlit.runtime.uploaded_file_manager.UploadedFile.
    Verified sufficient for all three get_uploaded_data() branches — see 02-RESEARCH.md
    Pattern 1. Real UploadedFile is itself a io.BytesIO subclass with the same .name/.size
    surface, so this is not a divergent shim."""
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name
        self.size = len(data)

def _rows_with_logical_blanks() -> list[dict]:
    """One shared row-list; a logical blank is represented here as the sentinel
    object `BLANK`, translated per format at write time."""
    ...  # reuse tests/fixtures.py's _BASE_ROW / _row() pattern; mark blank cells with BLANK

def make_sqlite_bytes(rows: list[dict]) -> bytes:
    """SQL NULL for BLANK; CREATE VIEW over the raw table (load_view() requires
    a view, verified against PRAGMA table_info this session)."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite"); tmp.close()
    conn = sqlite3.connect(tmp.name)
    cols = list(rows[0].keys())
    conn.execute(f"CREATE TABLE mlos_raw ({', '.join(f'{c} TEXT' for c in cols)})")
    conn.executemany(
        f"INSERT INTO mlos_raw VALUES ({', '.join('?' for _ in cols)})",
        [tuple(None if v is BLANK else v for v in row.values()) for row in rows],
    )
    conn.execute(f'CREATE VIEW "{MLOS_VIEW}" AS SELECT * FROM mlos_raw')
    # ... takeoff table + view likewise ...
    conn.commit(); conn.close()
    data = Path(tmp.name).read_bytes(); os.unlink(tmp.name)
    return data

def make_csv_bytes(rows: list[dict]) -> bytes:
    """Empty string for BLANK — matches keep_default_na=False's own contract."""
    df = pd.DataFrame([{k: ("" if v is BLANK else v) for k, v in r.items()} for r in rows])
    return df.to_csv(index=False).encode("utf-8")

def make_xlsx_bytes(mlos_rows, takeoff_rows) -> bytes:
    """Empty string for BLANK; sheet names chosen from get_uploaded_data's own alias set."""
    ...
```

**Comparison strictness** — the CONTEXT.md's open question about `Fail %` and `Total Rows`:
run all three formats through the **same fixed row set** (identical row count across formats by
construction, since the byte payloads are three encodings of one row list), so `Total Rows`
equality is guaranteed by construction and should be asserted as a cheap sanity check, not
reconciled. `Fail %` is a pure function of `Failing Rows`/`Total Rows` (`qc/predicates.py:pct`),
so asserting equality on `{Rule#, Failing Rows, Total Rows, Status}` per check is sufficient —
`Fail %` equality follows and need not be compared separately (though doing so is harmless).
Recommended assertion shape:

```python
def _summary(checks: list[dict]) -> dict:
    return {c["Rule#"]: (c["Failing Rows"], c["Total Rows"], c["Status"]) for c in checks}

assert _summary(sqlite_checks) == _summary(csv_checks) == _summary(xlsx_checks)
```

### Pattern 2: Cross-Table Match Masks Must Exclude Absent Source Cells (INTEG-02)

**This is a derived implementation requirement, not explicitly spelled out as code in
CONTEXT.md — it follows directly from D-03's own worked example, which is authoritative.**
D-03 states: *"A blank `ward_code` fires Rule 1 ..., `4.missing` and B0 — **three** failing
checks for one cell, and that is correct."* It does not include Rule 4 in that list. The current
(pre-fix) Rule 4 mask is:

```python
valid = set(takeoff["wardcode"].dropna().str.strip())
mask  = ~mlos["ward_code"].astype(str).str.strip().isin(valid)
```

If the fix only repairs `valid` (excluding blanks from the valid *target* set, e.g. via
`vec_is_absent`), a blank `mlos["ward_code"]` would still satisfy `~"".isin(valid)` → `True` →
**Rule 4 would also fail**, making it four checks, not three, contradicting D-03's explicit
count. The mask must therefore also exclude rows whose **source** value is itself absent:

```python
from qc.predicates import vec_is_absent

absent_source = vec_is_absent(mlos["ward_code"])
valid_targets = set(
    takeoff.loc[~vec_is_absent(takeoff["wardcode"]), "wardcode"].astype(str).str.strip()
)
not_matched = ~mlos["ward_code"].astype(str).str.strip().isin(valid_targets)
mask_rule4         = ~absent_source & not_matched     # only non-blank values that fail to match
mask_rule4_missing = absent_source                     # D-07: unconditional
```

This same pattern applies to Rules 2, 3 and to TP2/TP3/TP4 (mirrored, source/target swapped).
Apply it consistently to avoid the double-count D-03 explicitly rules out.

### Pattern 3: Column-Name Collision Must Be Detected Before Renaming (INTEG-03 / S3)

**Established Fact 2** (verified this session): `DataFrame.rename` does not raise on a colliding
target — renaming both `Ward Code` and `ward_code` to `ward_code` silently produces duplicate
column labels, and the next `df["ward_code"]` returns a `DataFrame`, not a `Series`, so
`.astype(str).str.strip()` raises `AttributeError`. **Consequence: collision detection must run
against the proposed rename map before any rename is applied**, not as a post-hoc check.

```python
# qc/columns.py (new) — pure, Streamlit-free per ENGINE-05
import re

_WS_HYPHEN_RE = re.compile(r"[\s\-]+")
_REPEAT_UNDERSCORE_RE = re.compile(r"_+")

def normalize_name(col: str) -> str:
    c = col.strip().lower()
    c = _WS_HYPHEN_RE.sub("_", c)
    c = _REPEAT_UNDERSCORE_RE.sub("_", c)
    return c

def normalize_columns(df, original_names=None):
    """Returns (renamed_df, renames_applied: dict[str,str], collisions: list[tuple[str,str,str]]).
    Collision pairs are left un-normalised in renamed_df — every other header renames normally."""
    original = list(df.columns) if original_names is None else original_names
    seen: dict[str, str] = {}
    collided_originals: set[str] = set()
    collisions = []
    for orig in original:
        norm = normalize_name(orig)
        if norm in seen:
            collisions.append((seen[norm], orig, norm))
            collided_originals.add(seen[norm]); collided_originals.add(orig)
        else:
            seen[norm] = orig
    rename_map = {
        orig: normalize_name(orig) for orig in original if orig not in collided_originals
    }
    renamed_df = df.rename(columns=rename_map)
    renames_applied = {o: n for o, n in rename_map.items() if o != n}
    return renamed_df, renames_applied, collisions
```

S3 registers in the Schema layer (`qc/schema.py`), reporting `len(collisions)` as `Failing Rows`
with `Total Rows` following S1/S2's non-row-denominator precedent (e.g. "0 collisions" as the
denominator concept, or simply the collision pair count — planner's call per CONTEXT.md's
discretion note). S1 will separately and correctly report the un-normalised original name(s) as
still missing, because they never entered the canonical set.

### Pattern 4: One-Snapshot Guard Touches Three Session-State Keys, Not One

D-13's text names two call sites (`app.py:693`, reused as `qc_cache_key` at `app.py:722`), but
02-CONTEXT.md's own "Established Patterns" section states explicitly: *"`st.session_state`
caching is keyed and read/written in two separate places (`get_uploaded_data`, and the QC block at
`:722`). **Both keys become the sha256 under D-13.**"* Read together with the `submitted_key`
write at `app.py:563`/`:693` (which the sidebar button sets and the main body reads at `:694`),
this is **three** call sites carrying the pre-fix `(name, size[, tp_key])` tuple shape that all
become sha256-derived:

| Call site | Current key (line) | Becomes |
|---|---|---|
| `get_uploaded_data`'s own cache (`app.py:149`) | `(uploaded_file.name, size)` | `sha256(uploaded_file.getvalue())` |
| Sidebar "Run QC" button (`app.py:562-565`) writes `submitted_key` | `(name, size, tp_key)` | same sha256 tuple/pair (see below) |
| Main-body `_current_key`/`qc_cache_key` (`app.py:692-693`, `:721`) | `(name, size, tp_key)` | same sha256 |

**Two-file identity (D-13's "both files when a separate Takeoffpoint is supplied"):**
recommend a **tuple of two hex digests**, `(sha256(mlos_bytes), sha256(tp_bytes) or None)`, rather
than concatenating the byte strings before hashing — a tuple of independently-computed digests
is unambiguous and trivially equality-comparable as a dict/session_state key (tuples of strings
are hashable), with no risk of a boundary-splitting ambiguity a naive `hash(a_bytes + b_bytes)`
concatenation could theoretically introduce.

**Hashing does not disturb the stream the loaders need** — confirmed this session:
`uploaded_file.getvalue()` returns the full byte content **without moving the read position**
(`.tell()` is unchanged after calling it), for both a plain `io.BytesIO` and Streamlit's own
`UploadedFile`. This means the hash can be computed at the very top of `get_uploaded_data` (or
even earlier, in the sidebar submit handler), **before** any `.seek(0)`/`.read()` the loaders
perform — no ordering hazard exists. `getvalue()` is strictly preferable to
`read()` + `seek(0)` here: it removes the need to reason about seek ordering at all.

**`@st.cache_data` interaction:** no adverse interaction exists, and the plan should NOT introduce
`@st.cache_data` as an alternative to the manual sha256-keyed `session_state` pattern. They are two
independent caching layers (`st.cache_data` hashes function arguments across the whole app
lifetime; `session_state` is a per-session dict the app already manages by hand for this exact
purpose). Layering `@st.cache_data` on top would add Streamlit's own argument-hashing semantics
(which have documented edge cases for custom/file-like objects) on top of an already-correct
manual key, for no benefit. `load_boundary_refs` (`app.py:289`) is a different, pre-existing use
of `@st.cache_data` with zero arguments (a pure "load once, reuse forever" cache) and is
unaffected by this phase.

### Recommended Project Structure (additions only)

```
qc/
├── columns.py          # NEW — normalize_name(), normalize_columns() (Pattern 3)
├── predicates.py       # + vec_is_absent() (D-04/D-05)
├── domain.py            # + ABSENCE_SENTINELS constant (D-05)
├── schema.py            # + S3 registration and check
├── mlos.py               # Rule 1 -> vec_is_absent; R2/R3/R4 masks fixed (Pattern 2);
│                         #   + 2.missing/3.missing/4.missing registrations
├── takeoff.py            # TP2/TP3/TP4 masks fixed (Pattern 2);
│                         #   + TP2.missing/TP3.missing/TP4.missing registrations
└── boundary.py           # + B4, B5 registrations; canonical order B0..B5
tests/
├── fixtures.py           # extended: rows exercising the six new .missing checks (Priority 2)
├── golden_fixture.py     # NEW — three-format byte builders (Pattern 1)
├── test_golden_three_format_parity.py   # NEW — ENGINE-06
├── test_absent_sentinel_guard.py         # NEW — D-05's required standing test
├── test_column_collision.py              # NEW — S3, exercised via direct DataFrame construction
├── test_one_snapshot_guard.py            # NEW — D-15's AST-based structural guard
└── test_extraction_parity.py             # REWRITTEN per-layer assertions (Priority 2) —
                                            #   qc_baseline.json / capture_baseline.py /
                                            #   test_baseline_records_the_duplicate_ids.py
                                            #   stay untouched
```

### Anti-Patterns to Avoid
- **Fixing only the valid-set construction for R2/R3/R4/TP2-4** without also excluding absent
  *source* cells from the match mask — silently turns D-03's "three checks" into four (Pattern 2).
- **Renaming columns before detecting collisions** — established defect (Fact 2): a colliding
  rename produces a duplicate-labelled DataFrame that crashes downstream `.str` accessors.
- **Regenerating `tests/baseline/qc_baseline.json`** to make `test_extraction_parity.py` pass —
  both `capture_baseline.py` and `test_baseline_records_the_duplicate_ids.py`'s module docstrings
  explicitly forbid this; it erases the pre-fix F3 magnitude record (Priority 2).
- **Introducing `qc.run_all()`** as a "cleanup" while touching the five call sites for D-14/D-15 —
  explicitly declined by Phase 1 and re-affirmed by D-15.
- **Widening the sentinel/absence predicate per-column** (e.g. skip sentinel matching on
  `state_code`) — explicitly rejected by D-05; the exemption is `"NA"` case-sensitive, globally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vectorised absence check across 28 columns | Per-row `.apply(lambda row: ...)` loop | `pd.concat([vec_is_absent(mlos[c]) for c in cols], axis=1).any(axis=1)` | Matches the codebase's existing vectorised-predicate convention (`vec_is_uuid`, `vec_is_editor`); a per-row loop is the exact anti-pattern Phase 1's research flagged |
| Content hashing of an uploaded file | Custom rolling hash / manual chunked read loop | stdlib `hashlib.sha256(uploaded_file.getvalue()).hexdigest()` | One call, no stream-position risk (verified this session), no dependency |
| Detecting duplicate normalised column names | Manual nested loop with early break | `collections.Counter` over normalised names, or the `seen`-dict pattern in Pattern 3 | Already how Python idiomatically finds duplicates; O(n) either way but the dict form also captures which two original names collided, which the S3 check description needs |

**Key insight:** every new piece of logic in this phase is a small, pure, vectorised
pandas transform that slots beside an existing sibling of the same shape (`vec_is_uuid` next to
`vec_is_absent`; R2/R3/R4 next to `.missing`; B0-B3 next to B4/B5). There is no case in this phase
that benefits from a library beyond what is already pinned.

## Common Pitfalls

### Pitfall 1: `qc_baseline.json` Diff Tests Break on Length, Not Content
**What goes wrong:** `test_extraction_parity.py`'s five per-layer tests assert
`len(actual_checks) == len(expected_checks)` before comparing any field. Adding `S3` (schema),
`.missing` checks (mlos, takeoff) and `B4`/`B5` (boundary) changes every one of those lengths.
**Why it happens:** the tests were written to prove *extraction* parity (Phase 1: move code,
change nothing), and Phase 2 exists specifically to change detection behaviour.
**How to avoid:** see Priority 2's disposition below — rewrite the per-layer assertions to encode
Phase 2's intended output directly; do not touch the frozen `qc_baseline.json`/`capture_baseline.py`/
`test_baseline_records_the_duplicate_ids.py` trio.
**Warning signs:** a "fix" that edits `qc_baseline.json` or deletes assertions from
`test_baseline_records_the_duplicate_ids.py` to make CI green.

### Pitfall 2: The Existing Fixture Has No Genuinely Blank Cross-Table Cell
**What goes wrong:** `tests/fixtures.py`'s row 2 ("Bravo") has `takeoffpoint="Ghost-TP"`,
`takeoffpoint_code="GHOST-CODE"`, `ward_code="00000"` — all **mismatched but non-blank** values,
which exercise the existing match-failure rules (2, 3, 4) but **cannot** exercise `2.missing`,
`3.missing`, `4.missing` as failing checks (a blank cell is required, and none exists in the
current 10 rows). The same is true on the Takeoffpoint side — `build_takeoff_fixture()`'s orphan
row has non-blank mismatched values, not a blank `name`/`code`/`wardcode`.
**Why it happens:** the fixture was built in Phase 1, before INTEG-02 existed as a concept.
**How to avoid:** `test_registry_covers_emitted_ids.py`'s "every registered id is emitted"
guard will pass trivially even without this fix (D-07 makes `.missing` checks emit
unconditionally, so they appear in the checks list with `Failing Rows: 0` regardless), but that
is a false sense of coverage — nothing would prove the fix actually *detects* a blank. The
planner must add at least one MLoS row with a genuinely blank `takeoffpoint`/`takeoffpoint_code`/
`ward_code` cell, and one Takeoffpoint row with a blank `name`/`code`/`wardcode` cell, updating the
docstring's row-by-row map (`tests/fixtures.py` lines 20-37) to match — following the module's own
stated goal ("every rule ... has at least one row that fails it and at least one row that does
not").
**Warning signs:** `2.missing`/`3.missing`/`4.missing`/`TP2.missing`/`TP3.missing`/`TP4.missing`
show `Failing Rows: 0` in every test run — the check runs, but nothing ever proves it can fail.

### Pitfall 3: `test_registry_covers_emitted_ids.py` Cannot See Both B4 and B5 in One Run
**What goes wrong:** `_emitted_identifiers()` in that file runs `run_ward_boundary_qc` exactly
once, against the real (non-empty) bundled boundary CSVs (`conftest.py`'s `boundary_refs`
fixture). Under D-17/D-19: B4 emits (PASS or FAIL) whenever a reference **exists** — true for this
fixture — so B4 will appear in the emitted set. But B5 only emits when the reference is
**unavailable** (`load_boundary_refs` returning empty frames) — a condition this fixture never
reaches, so a single run can never make B5 appear. `test_every_registered_identifier_is_emitted_
by_the_fixture` will therefore fail for `B5` specifically, once `B5` is registered, unless the test
itself is extended.
**Why it happens:** the test was written (Phase 1) assuming one fixture invocation suffices for
"every registered id is emitted" — true when every check's emission condition is compatible with
a single reference state, false once a check (B5) is defined by the reference's *absence*.
**How to avoid:** extend `_emitted_identifiers()` (or add a second, explicit test) to run
`run_ward_boundary_qc(mlos_df, pd.DataFrame(), pd.DataFrame())` as a second scenario and union its
emitted set with the first, mirroring the existing `test_boundary_layer_reports_a_missing_ward_
code_column` pattern (which already calls the function directly with a modified argument rather
than only through the shared fixture).
**Warning signs:** `test_every_registered_identifier_is_emitted_by_the_fixture` fails naming only
`B5` as unemitted, right after B5's registration lands.

### Pitfall 4: B4's National-Fallback Trigger Needs Its Own Fixture Row, Not the Standard One
**What goes wrong:** the standard fixture's single ward (`81110`, Zamfara) is present in the real
boundary reference, so `filtered_ref` (state-filtered) is never empty for `state_name="Zamfara"`
rows — the fallback path (`qc/boundary.py:89-91`) never fires against the standard fixture, so B4
would always report PASS ("validated against Zamfara's N wards"), never demonstrating the FAIL
branch.
**Why it happens:** B4 is triggered by `state_name` values that have **zero** matching rows in the
reference (e.g. a misspelled or non-Nigerian state name) — a scenario the existing 10-row fixture
was never designed to include, since Phase 1's fixture intentionally anchors every row to one real,
valid ward for boundary-check realism.
**How to avoid:** add a dedicated unit test (not necessarily the shared fixture) that calls
`run_ward_boundary_qc` with a small DataFrame whose `state_name` does not exist anywhere in the
real reference, and assert `B4`'s `Status` is `FAIL` and its description names both B1 and B2 (per
D-16).
**Warning signs:** B4 always shows PASS in every test; nothing exercises the widening path itself.

### Pitfall 5: Circular Import via Package `__init__` (carried over from Phase 1, still applies)
**What goes wrong:** a new `qc/columns.py` module importing `from . import domain` (via the
package's own `__init__.py`, which imports every sibling module) rather than `from .domain import
X` directly can produce partially-initialised-module errors depending on import order.
**Why it happens:** `qc/__init__.py` imports every layer submodule; a submodule importing back
through `qc/__init__.py` (even implicitly via `import qc; qc.domain.X`) creates a cycle.
**How to avoid:** every new module under `qc/` uses relative sibling imports
(`from .domain import ABSENCE_SENTINELS`, `from .predicates import vec_is_absent`) exactly as
`qc/predicates.py`'s own docstring already documents and every existing layer module already does.
**Warning signs:** `ImportError: cannot import name 'X' from partially initialized module 'qc'`.

## Code Examples

### Absence predicate (D-04/D-05), matching the orchestrator's empirically-verified behaviour

```python
# qc/domain.py
ABSENCE_SENTINELS = {"null", "none", "n/a", "nan", "-"}   # case-insensitive, "NA" exempted

# qc/predicates.py
from .domain import ABSENCE_SENTINELS

def vec_is_absent(series: "pd.Series") -> "pd.Series":
    """A value is absent per D-04/D-05: NA/None/NaN, empty, whitespace-only, or a
    case-insensitive sentinel — except the exact literal "NA", which survives as present."""
    t = series.astype(str).str.strip()
    lowered = t.str.lower()
    is_sentinel = lowered.isin(ABSENCE_SENTINELS) & ~t.eq("NA")
    return series.isna() | t.eq("") | is_sentinel
```

This exact behaviour (`None`/`''`/`'  '`/`'N/A'`/`'nan'`/`'-'` -> absent;
`'NA'`/`'na'`/`'N'`/`'0'`/`'Gidan Ali'` -> present) is Established Fact 4 below, already verified
by the orchestrator this session against a real `str`-dtype Series.

### Rule 1 using the vectorised predicate across all 28 `_NOT_NULL_COLS`

```python
absent_frame = pd.concat(
    [vec_is_absent(mlos[c]) for c in _NOT_NULL_COLS], axis=1, keys=_NOT_NULL_COLS
)
_null_mask = absent_frame.any(axis=1)
# "Null Fields" column: reuse the boolean frame directly instead of re-deriving per row
_sub1["Null Fields"] = absent_frame[_null_mask].apply(
    lambda row: ", ".join(col for col, is_absent in row.items() if is_absent), axis=1
)
```

### D-05's required standing test (sentinel exemption guard)

```python
# tests/test_absent_sentinel_guard.py
import pandas as pd
from qc.predicates import vec_is_absent
from qc.domain import FLAG_COLS  # already-ordered flag column list

def test_exact_NA_survives_as_present_in_every_flag_column():
    for col in FLAG_COLS:
        s = pd.Series(["NA"])
        assert not vec_is_absent(s).iloc[0], f"{col}: exact 'NA' must NOT read as absent"

def test_exact_NA_survives_as_present_as_state_code():
    assert not vec_is_absent(pd.Series(["NA"])).iloc[0]

def test_lowercase_na_is_not_swept_up_as_a_sentinel():
    # "na" is not itself in the sentinel set ({"null","none","n/a","nan","-"}) — it is a
    # distinct two-letter string from "nan" and from the exempted literal "NA". D-05 requires
    # it survive as present, same as "NA", but for a different reason (never matched, not
    # exempted). Verified empirically this session: vec_is_absent(Series(["na"])) is False.
    assert not vec_is_absent(pd.Series(["na"])).iloc[0]

def test_sentinel_list_catches_null_none_nan_dash():
    for token in ("null", "None", "NaN", "n/a", "N/A", "-"):
        assert vec_is_absent(pd.Series([token])).iloc[0], f"{token!r} must read as absent"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mlos[cols].isnull()` for Rule 1 | `vec_is_absent` predicate across all NOT-NULL columns | This phase (D-04) | Rule 1 now fails identically regardless of upload format |
| `set(takeoff[col].dropna().str.strip())` valid-set construction | Valid set built from non-absent target values; source mask also excludes absent rows | This phase (D-01/D-03) | Blank cannot silently match blank; blank gets its own finding instead of a false pass or a doubled fail |
| Raw-frame column presence tests (`if "takeoffpoint" in mlos.columns`) alongside a normalised-set schema check | Single normalisation pass at load, before any rule runs | This phase (D-08/D-09) | Schema alignment (S1/S2) and rule column-presence guards see the same names |
| `(name, size)` / `(name, size, tp_key)` session cache keys | `sha256` over uploaded bytes | This phase (D-13) | Same-name/same-size, different-content uploads no longer collide in session state |

**Deprecated/outdated:** the pre-fix `set(...).dropna()` pattern for cross-table valid-set
construction — silently unsafe under `keep_default_na=False`, which is itself correct and stays.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A tuple of two sha256 hex digests (rather than a concatenated-bytes single hash) is the right shape for the two-file submission identity key | Pattern 4 | Low — both are correct identity schemes; a tuple is simpler to reason about and this is an implementation detail, not a behavioural one. Planner may choose concatenation instead without violating D-13. |
| A2 | `Total Rows` equality across the three golden-fixture formats is guaranteed by construction (same row count fed to all three writers) and does not need reconciliation logic | Pattern 1 | Low — if the planner's fixture ever uses format-specific row counts (e.g. a header-only `.xlsx` sheet), this assumption breaks; recommend asserting it explicitly as a sanity check rather than assuming it silently |
| A3 | `S3`'s "Failing Rows"/"Total Rows" denominator should mirror S1/S2's non-row-count precedent (collision-pair count vs. columns-required count), rather than the underlying MLoS row count | Pattern 3 | Low — CONTEXT.md explicitly leaves this to the planner; flagged here only so the planner does not default to `len(mlos)` out of habit from the MLoS-layer rules |

**If this table is empty:** N/A — see above. All three assumptions are low-risk implementation
choices explicitly left to the planner's discretion by CONTEXT.md; nothing here is a compliance,
retention, or performance claim requiring user confirmation.

## Open Questions

1. **Should `test_extraction_parity.py`'s per-layer tests become hand-derived example assertions, or a second frozen `qc_baseline_v2.json`?**
   - What we know: both are workable; the frozen-`qc_baseline.json`/`capture_baseline.py`/`test_baseline_records_the_duplicate_ids.py` trio must NOT be touched either way (their docstrings explicitly forbid regeneration).
   - What's unclear: whether the planner prefers to keep the "diff-against-JSON" pattern Phase 1 established (requiring a new, distinctly-named JSON artifact and its own capture script) or move to direct example-based assertions (no new JSON artifact, but a bigger diff in `test_extraction_parity.py` itself).
   - Recommendation: hand-derived assertions (Priority 2, option (a)) — better failure messages for a phase that is specifically about "the count was wrong," and no second frozen-artifact-provenance story to maintain. See Priority 2 write-up below for the full reasoning.

2. **Exact wording/denominator for S3, B4, B5's `Failing Rows`/`Total Rows` fields.**
   - What we know: CONTEXT.md explicitly defers this to the planner, citing S1/S2 as precedent for a non-row denominator.
   - What's unclear: whether B4/B5 (run-level, not column-count-level like S1-S3) should report `Failing Rows: 1/Total Rows: 1` (binary run-level pass/fail) or something else, e.g. `Total Rows` = count of wards in the applicable reference.
   - Recommendation: `Failing Rows: 1, Total Rows: 1` for a binary run-level condition (B4/B5), reading "1 finding out of 1 possible finding" — simplest, and does not imply a false row-level percentage.

## Priority 2 (detailed): Baseline and Parity Test Disposition

**Do not touch:** `tests/baseline/qc_baseline.json`, `tests/baseline/capture_baseline.py`,
`tests/test_baseline_records_the_duplicate_ids.py`. All three carry explicit docstring language
forbidding regeneration ("Do NOT regenerate it after an extraction" / "Do NOT 'fix' these tests
when app.py's rule identifiers change"). They exist permanently as the numeric record of Phase 1's
F3 identifier-collision defect (40 emitted checks, 31 distinct identifiers, a difference of 9) and
will keep passing unchanged through Phase 2 and beyond, because they assert facts about the frozen
JSON file, not about live `qc/` code.

**Must change:** `tests/test_extraction_parity.py`'s five per-layer test functions
(`test_schema_layer_matches_baseline`, `test_mlos_layer_matches_baseline`,
`test_settlement_layer_matches_baseline`, `test_takeoff_layer_matches_baseline`,
`test_boundary_layer_matches_baseline`). Every one of these will fail on
`assert len(actual_checks) == len(expected_checks)` (or the equivalent set-based check for
`mlos`) the moment `S3`, `.missing`×6, `B4`, `B5` are registered — this is not a bug in the new
code, it is the frozen baseline correctly describing a *smaller* rule set than Phase 2 produces.

**Recommendation: rewrite these five functions as direct, hand-derived assertions against the
(extended) fixture**, not as a diff against any JSON file. Concretely:

- `test_schema_layer_matches_baseline` → assert `S1`, `S2` still report the same
  (unchanged, per D-20's zero-drift verification) counts, AND assert `S3` reports 0 collisions
  against the standard fixture (no colliding headers there) — plus a **separate**, new test with
  a deliberately-colliding two-column DataFrame proving `S3` fires (Pitfall 3's sibling for
  Schema).
- `test_mlos_layer_matches_baseline` → keep the fourteen frozen-identifier field-by-field
  comparisons the Phase 1 version already does (these are still valid — the frozen identifiers'
  *values* don't change for this fixture, only the schema-layer's *count* changes elsewhere), but
  compute the fourteen expected values freshly from the fixture's row-by-row docstring map rather
  than from `BASELINE["mlos"]`, and add explicit new assertions for the six new identifiers
  against the extended fixture (Pitfall 2).
- `test_boundary_layer_matches_baseline` → same pattern: B0-B3's values are unchanged for this
  fixture (verify against the docstring map), B4 reports PASS for the standard fixture (real
  reference exists, Zamfara is in it), B5 is asserted via the dedicated
  empty-reference-frames call (Pitfall 3/4), not through the shared fixture.
- Reuse `_nan_safe`, `normalize_checks`, `normalize_detail` as-is — these normalisation helpers
  are format-agnostic and remain correct.

This keeps the "prove it against a known-good expected value" spirit of Phase 1's parity work
while making the expected values Phase 2's own intended behaviour, not a diff against a
deliberately-frozen pre-fix number that no longer describes the target state.

## Priority 3 (detailed): The Ten New Identifiers

`2.missing`, `3.missing`, `4.missing`, `TP2.missing`, `TP3.missing`, `TP4.missing`, `S3`, `B4`,
`B5` — nine, not ten (`02-CONTEXT.md`'s prose lists nine explicitly; the task prompt's count of
"ten" appears to be a miscount carried from the prompt, not from CONTEXT.md — the planner should
verify against D-02/D-10/D-16/D-18's exact enumeration, which totals nine: three MLoS-side
`.missing`, three Takeoffpoint-side `.missing`, `S3`, `B4`, `B5`).

**Exactly which standing tests fail until which artifacts change:**

| Test | Fails until... |
|---|---|
| `test_results_registry.py` | No change required — these tests exercise the registry's own duplicate-detection and empty-state behaviour with throwaway ids; they do not enumerate the real rule set and are unaffected by new registrations. |
| `test_rule_identifiers.py` | `test_every_registered_identifier_is_distinct` and `test_excel_sheet_names_fit_and_stay_distinct` will keep passing automatically (they iterate `qc.canonical_order()`, not a hard-coded list) once the nine new ids are registered without colliding. No edits needed to this file itself, **provided** none of the nine collides with an existing identifier or with each other — verified: `2.missing` (7 chars) through `TP4.missing` (11 chars) are all well under the 31-char Excel sheet-name limit (longest derived name: `Rule TP4.missing` = 16 chars). |
| `test_registry_covers_emitted_ids.py` | Fails for `B5` specifically (Pitfall 3) until the test itself is extended with a second, reference-absent scenario. Fails for none of the other eight, since D-07's "unconditional emission" means they always appear in the emitted set regardless of whether any row actually triggers them. |
| `test_deterministic_order.py` | No change required — this test's subprocess snippets call the five `run_*_qc` functions directly and print whatever they emit; it will simply print more identifiers per run and the byte-for-byte cross-seed comparison still holds, since determinism comes from `sort_by_registry`/registration order, not from the identifier count. |
| `test_rules_reference_matches_registry.py` | **Fails immediately** once the nine identifiers are registered, until `app.py`'s five sidebar "Rule"/"Check" markdown tables (`app.py:~580-651`) are updated to list all nine new rows (S3 in the Schema table, `.missing` rows in MLoS/Takeoffpoint tables, B4/B5 in the Boundary table). This is a required app.py edit, not just a `qc/` edit — the test's own docstring calls out exactly this two-directional failure mode. |

**`canonical_order()` afterwards:** Schema → MLoS → Settlement → Takeoffpoint → Boundary (layer
order unchanged), with each new id taking its declaration-order position within its layer. Given
the existing declaration order in each module (`register()` calls execute top-to-bottom at import
time), the natural placement is: `S3` after `S2`; `2.missing` immediately after `2` (and similarly
for 3/4); `TP2.missing` immediately after `TP2` (similarly TP3/TP4); `B4` and `B5` after `B3` (this
also satisfies D-16's requirement that canonical order end `B0, B1, B2, B3, B4, B5`).

## Priority 5 (detailed): Defect Residue Check

| Defect | Closed by | Residue for later phases |
|---|---|---|
| F2 (INTEG-01) | D-04/D-05 `vec_is_absent` replacing `.isnull()` in Rule 1 | None within scope — the predicate change is format-independent by construction (operates on the already-loaded `str`-dtype Series, not on the loader). Fully closed. |
| F4 (ENGINE-03) | D-12/D-13/D-14/D-15 — sha256 identity, two-frame session state, AST structural guard | None within scope, **provided** the AST guard (D-15) is written to cover every one of: the five `run_*_qc` call sites, the on-screen table render, `build_corrected_excel`'s argument, and the report's as-submitted sheet — a partial guard (e.g. covering only the five QC calls but missing the on-screen table) would leave a variant of F4 open. |
| F5 (ENGINE-04) | D-12 (uuid4 once, cached) + deletion of the second `auto_correct_mlos` call at `app.py:982` | Explicitly inherited by v2: HIST-01's `eha_guid`-churn detection will see churn from session-boundary re-generation as well as real data change, because D-12 chose session-scoped (not content-derived) identity. Not this phase's concern — already flagged in CONTEXT.md's Deferred Ideas. |
| F7 (INTEG-03) | D-08/D-09/D-10/D-20 — typographic normalisation + collision detection + README-as-source-of-truth | None regarding the 47 canonical names (verified zero drift between README.md and `qc/domain.py` this session — see grep output below). Process residue: a *future* divergence between README.md and `qc/domain.py` must be treated as a defect, per D-20 — this is a documentation-discipline item, not a code item, and has no phase currently assigned to guard it structurally (no test asserts README.md's column tables match `MLOS_REQUIRED_COLS`/`TAKEOFF_REQUIRED_COLS` — worth flagging to the planner as an optional cheap addition, following the `test_rules_reference_matches_registry.py` pattern). |
| F9 (INTEG-02) | D-01/D-02/D-03/D-06/D-07 | Nearest-non-matching-candidate reconciliation aid explicitly deferred to its own future phase (already noted in CONTEXT.md). |
| F13 (INTEG-04) | D-16/D-17/D-18/D-19 | Two residues, both already named in CONTEXT.md and owned by later phases: (1) B2's unmatched-bounding-box silent pass (`qc/boundary.py:155`) — Phase 7's GEO-01 (point-in-polygon) and GEO-03 (dataset/version provenance); (2) whether a B5 (missing-reference) run should *not* score as a full pass — Phase 3's VERDICT-05 ("no credit for a layer that ran zero checks"). Neither is this phase's work; both are correctly deferred, not silently dropped. |

`[VERIFIED: README.md ##"Required MLoS Columns (43)"/"Required Takeoffpoint Columns (4)" vs qc/domain.py MLOS_REQUIRED_COLS/TAKEOFF_REQUIRED_COLS, read this session]` — the 43 MLoS + 4 Takeoffpoint column names in README.md's tables match `qc/domain.py`'s sets exactly; no drift found, confirming D-20's discussion-time verification still holds.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (pinned `>=8.0.0,<10.0.0`) `[VERIFIED: .venv/bin/python -m pytest --version, run this session]` |
| Config file | `pytest.ini` (`testpaths = tests`, `python_files = test_*.py`) |
| Quick run command | `.venv/bin/python -m pytest tests/ -q` (currently 34 passed in 2.63s, verified this session) |
| Full suite command | same — the suite is small enough that "quick" and "full" are the same command for this phase |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTEG-01 | Rule 1 detects missing values identically across formats | unit + golden | `pytest tests/test_absent_sentinel_guard.py tests/test_golden_three_format_parity.py -x` | ❌ Wave 0 (both new) |
| INTEG-02 | Blank cannot satisfy R2/R3/R4/TP2-4 match | unit | `pytest tests/test_extraction_parity.py -k mlos_layer_matches -x` (rewritten, Priority 2) | ❌ Wave 0 (rewrite) + extended fixture |
| INTEG-03 | Column normalisation + S3 collision + rename reporting | unit | `pytest tests/test_column_collision.py -x` | ❌ Wave 0 (new) |
| INTEG-04 | B4/B5 visible-warning fallback | unit | `pytest tests/test_extraction_parity.py -k boundary_layer_matches -x` (rewritten) + a dedicated fallback-trigger test (Pitfall 4) | ❌ Wave 0 (rewrite + new) |
| ENGINE-03 | One frame of record across renders | unit (AST) | `pytest tests/test_one_snapshot_guard.py -x` | ❌ Wave 0 (new) |
| ENGINE-04 | Auto-correction runs exactly once | unit (AST, same guard as ENGINE-03) | `pytest tests/test_one_snapshot_guard.py -x` | ❌ Wave 0 (new, shared with ENGINE-03) |
| ENGINE-06 | Golden three-format fixture | integration | `pytest tests/test_golden_three_format_parity.py -x` | ❌ Wave 0 (new) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -q`
- **Per wave merge:** same (full suite, ~3 seconds — no reason to sample)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/golden_fixture.py` — three-format byte builders (Pattern 1); no existing file covers this
- [ ] `tests/test_golden_three_format_parity.py` — ENGINE-06's actual assertion
- [ ] `tests/test_absent_sentinel_guard.py` — D-05's required standing test
- [ ] `tests/test_column_collision.py` — S3 detection, direct DataFrame construction (colliding headers can't be expressed via the row-dict fixture)
- [ ] `tests/test_one_snapshot_guard.py` — D-15's AST-based structural guard over `app.py`
- [ ] Extend `tests/fixtures.py` — add rows exercising the six new `.missing` checks (Pitfall 2) and update its row-by-row docstring map
- [ ] Extend `tests/test_registry_covers_emitted_ids.py` — second scenario for B5 (Pitfall 3)
- [ ] Rewrite five functions in `tests/test_extraction_parity.py` (Priority 2) — do NOT touch `tests/baseline/*`
- [ ] Update `app.py`'s five sidebar rules-reference tables (`~:580-651`) — required by `test_rules_reference_matches_registry.py`

## Security Domain

`security_enforcement` is enabled (ASVS level 1, `security_block_on: "high"` per `.planning/config.json`, read this session). This phase adds no authentication, session, or access-control surface (that is Phase 4) — its ASVS relevance is narrow.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Out of scope for this phase (Phase 4) |
| V3 Session Management | No | `st.session_state` usage here is application caching, not an authenticated session concept |
| V4 Access Control | No | Out of scope for this phase (Phase 4/v2 ACL-01) |
| V5 Input Validation | Yes | This phase *is* input validation — the absence predicate, column normalisation, and collision detection are exactly V5's concern. No new external validation library is warranted; pandas vectorised masks are the existing, appropriate control. |
| V6 Cryptography | Marginal | `hashlib.sha256` is used for **content-addressing** (cache-key identity), not for a security boundary (no secret, no password, no signature). Standard library `hashlib` is the correct, non-hand-rolled choice; no key management or salting is needed because this is not an authentication credential. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Duplicate normalised column labels crash `.str` accessors on downstream user-controlled input (Established Fact 2) | Tampering / Denial of Service | S3's collision-detection-before-rename (Pattern 3) — a malformed or adversarial header set fails a named check instead of crashing the process |
| Two different officers' uploads colliding on cache key (`(name, size)`) | Tampering (cross-user data leakage within a session) | D-13's sha256 content identity (Pattern 4) |
| A hostile CSV/XLSX using sentinel-like strings (`"null"`, `"n/a"`) to intentionally mask a genuinely missing required field from Rule 1 | Repudiation (an officer could claim a field "was filled in" when it effectively wasn't) | This is explicitly the behaviour D-04/D-05 exist to catch — the sentinel list treats these strings as absent, not as satisfying the not-null requirement, which is the correct posture for a QC tool whose Core Value is "a file this tool calls clean is clean" |

## Sources

### Primary (HIGH confidence — read/verified this session)
- `.planning/phases/02-detection-correctness-and-three-format-harness/02-CONTEXT.md` — full read, all 20 decisions
- `.planning/REQUIREMENTS.md`, `.planning/phases/01-.../01-CONTEXT.md`, `.planning/STATE.md` — full read
- `app.py` (loaders lines 90-300, boundary/email/report builders 280-420, upload/QC orchestration 500-1010, sidebar reference tables 1195-1280) — read this session
- `qc/mlos.py`, `qc/takeoff.py`, `qc/schema.py`, `qc/boundary.py`, `qc/autocorrect.py`, `qc/domain.py`, `qc/predicates.py`, `qc/results.py`, `qc/settlement.py`, `qc/__init__.py` — full read this session
- `tests/fixtures.py`, `tests/conftest.py`, `tests/baseline/capture_baseline.py`, `tests/test_extraction_parity.py`, `tests/test_baseline_records_the_duplicate_ids.py`, `tests/test_results_registry.py`, `tests/test_rule_identifiers.py`, `tests/test_registry_covers_emitted_ids.py`, `tests/test_deterministic_order.py`, `tests/test_rules_reference_matches_registry.py`, `tests/test_no_streamlit_in_qc.py` — full read this session
- `README.md` (Required MLoS/Takeoffpoint column tables, State filtering section) — read this session
- Empirical verification via `.venv/bin/python3` (pandas 3.0.5, streamlit 1.63.0, pytest 9.1.1): SQLite `CREATE VIEW` + `PRAGMA table_info` round-trip; `io.BytesIO`-with-`.name` through all three `get_uploaded_data` branches; `getvalue()` position-preservation; Streamlit's `UploadedFile` source code confirming it subclasses `io.BytesIO` and documents `getvalue()`'s no-seek behaviour itself

### Secondary (MEDIUM confidence)
- None — every claim in this document traces to a file read this session or an empirical test run this session against the project's own pinned environment.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; every capability built from packages already pinned and verified installed
- Architecture: HIGH — every pattern verified either by reading the actual source this session or by running code against the pinned `.venv`
- Pitfalls: HIGH — each pitfall traces to a specific test file's actual assertion logic, read this session, not inferred

**Research date:** 2026-09-10
**Valid until:** Stable for the duration of Phase 2 planning/execution — re-verify if `pandas`, `streamlit`, or `pytest` pins change before this phase lands (30-day estimate for a repo at this activity level).
