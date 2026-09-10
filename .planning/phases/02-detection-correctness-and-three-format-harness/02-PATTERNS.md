# Phase 2: Detection Correctness and Three-Format Harness - Pattern Map

**Mapped:** 2026-09-10
**Files analyzed:** 19 (9 modified existing, 6 new test files, 1 extended test fixture, 1 new `qc/` module implied, 1 rewritten test file already counted, 1 possibly-new `qc/columns.py`)
**Analogs found:** 19 / 19 (this is a modification-heavy phase — every new artifact has a direct in-repo analog)

All analog paths below were verified tracked with `git ls-files` (see Metadata). No gitignored mirror paths are referenced.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `qc/domain.py` (+`ABSENCE_SENTINELS`) | config/constants | transform | itself (`qc/domain.py`, existing `VALID_YN_NA`/`FLAG_COLS` block) | exact |
| `qc/predicates.py` (+`vec_is_absent`) | utility | transform | itself (`vec_is_uuid`/`vec_is_editor` in same file) | exact |
| `qc/columns.py` (new) | utility | transform | `qc/schema.py` (pure, Streamlit-free, `qc/`-sibling-import shape) + `qc/predicates.py` (vectorised-function shape) | role-match (new module, but shape/import convention identical to existing `qc/` siblings) |
| `qc/mlos.py` (Rule 1 → `vec_is_absent`; R2/R3/R4 mask fix; +6 `.missing` registrations) | service/rule-engine | CRUD (row-mask classification) | itself — `run_mlos_qc`'s `add()` closure and R2-R4 blocks (lines 66-131) | exact |
| `qc/takeoff.py` (TP2/TP3/TP4 mask fix; +3 `.missing` registrations) | service/rule-engine | CRUD | itself — `run_takeoff_qc`'s `add()` closure and TP2-TP4 blocks (lines 32-61); mirrors `qc/mlos.py`'s R2-R4 fix | exact |
| `qc/schema.py` (+`S3` collision check) | service/rule-engine | CRUD (run-level, non-row denominator) | itself — `S1`/`S2`'s non-row-denominator shape (lines 24-60) | exact |
| `qc/boundary.py` (+`B4`, `B5`; canonical order B0..B5) | service/rule-engine | CRUD | itself — B0's early-return-and-single-check pattern (lines 40-48) for B5; the state-fallback site (lines 89-92) for B4 | exact |
| `qc/autocorrect.py` (no code change expected — consumed once by `app.py`, not itself edited by D-12/D-15; UUID caching moves to `app.py`) | service/transform | transform | itself | exact (no-op / verify) |
| `qc/results.py` | infra (registry) | n/a — consumed, not modified | itself | exact |
| `app.py` — `get_uploaded_data` (sha256 cache key, D-13) | loader/controller | file-I/O | itself, lines 148-195 | exact |
| `app.py` — sidebar submit + main-body `_current_key`/`qc_cache_key` (D-13) | controller | request-response (session cache) | itself, lines 561-565 and 691-693, 721-724 | exact |
| `app.py` — one-snapshot `mlos_raw`/`mlos_corrected` (D-14) | controller | event-driven (session lifecycle) | itself, lines 741-747 (first auto-correct call) and 982 (second, to be deleted) | exact |
| `app.py` — sidebar rules-reference tables (+9 new identifier rows) | component (UI) | request-response | itself, lines 580-650 | exact |
| `app.py` — column normalisation call sites (load paths) | controller | transform | `get_uploaded_data` (lines 148-195), `load_takeoffpoint_file` (lines 520-532), `load_boundary_refs` (lines 289-299) | exact |
| `tests/golden_fixture.py` (new) | test fixture/utility | file-I/O (byte round-trip) | `tests/fixtures.py` (plain-function, import-safe-without-pytest convention) | role-match (new file, established convention) |
| `tests/test_golden_three_format_parity.py` (new) | test | integration | `tests/test_extraction_parity.py` (loads real data, compares per-layer check summaries) | role-match |
| `tests/test_absent_sentinel_guard.py` (new) | test | unit (domain-constant guard) | `tests/test_rule_identifiers.py` / `tests/test_deterministic_order.py` (standing structural guards over a `qc/` constant/behaviour) | role-match |
| `tests/test_column_collision.py` (new) | test | unit (direct DataFrame construction, not fixture-based) | no existing test builds a bare inline DataFrame outside `tests/fixtures.py`'s row-dict shape — closest is `tests/test_registry_covers_emitted_ids.py`'s direct-call pattern (calls `run_ward_boundary_qc` with a hand-built argument rather than the shared fixture) | partial (no exact analog; documented below) |
| `tests/test_one_snapshot_guard.py` (new) | test | unit (AST-over-`app.py` structural guard) | **`tests/test_no_streamlit_in_qc.py`** — exact idiom reuse | exact |
| `tests/fixtures.py` (extended: blank cells for `.missing` checks) | test fixture | transform | itself | exact |
| `tests/test_extraction_parity.py` (5 functions rewritten) | test | integration | itself | exact |
| `tests/test_registry_covers_emitted_ids.py` (extended: 2nd empty-reference scenario for B5) | test | unit | itself, plus its own existing `test_boundary_layer_reports_a_missing_ward_code_column`-style direct-call pattern | exact |

**Do-not-touch (frozen, verified tracked, never edit):**
`tests/baseline/qc_baseline.json`, `tests/baseline/capture_baseline.py`, `tests/test_baseline_records_the_duplicate_ids.py` — docstrings explicitly forbid regeneration; they preserve Phase 1's F3 pre-fix numeric record and must survive Phase 2 unchanged.

## Pattern Assignments

### `qc/domain.py` (+`ABSENCE_SENTINELS`, constants)

**Analog:** itself — the existing module-level constant block.

**Pattern to copy** (lines 14-24, existing shape — add the new constant in the same UPPERCASE style, adjacent to `VALID_YN_NA`):
```python
VALID_YN_NA = {"Y","N","NA"}
...
FLAG_COLS = [
    "highrisk", "slums", "densely_populated", "hard2reach",
    "border", "nomadic", "scattered", "riverine", "fulani",
]
```
New constant follows this exact shape (per Research's Code Example):
```python
ABSENCE_SENTINELS = {"null", "none", "n/a", "nan", "-"}   # case-insensitive, "NA" exempted
```
No import cycle risk: `qc/domain.py` imports nothing from siblings (Pitfall 5 does not apply here — it is the leaf module).

---

### `qc/predicates.py` (+`vec_is_absent`)

**Analog:** itself — `vec_is_uuid`/`vec_is_editor` (lines 16-22).

**Imports pattern** (lines 1-10) — relative sibling import, never through `qc/__init__.py` (Pitfall 5):
```python
from .domain import UUID_RE, EDITOR_RE
```
New function imports `ABSENCE_SENTINELS` the same way: `from .domain import ABSENCE_SENTINELS`.

**Core vectorised-predicate pattern** (lines 16-22, copy this shape exactly):
```python
def vec_is_uuid(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(UUID_RE.pattern, na=False)
```
`vec_is_absent` follows the same "Series in, boolean Series out, no `.apply`" contract:
```python
def vec_is_absent(series: "pd.Series") -> "pd.Series":
    t = series.astype(str).str.strip()
    lowered = t.str.lower()
    is_sentinel = lowered.isin(ABSENCE_SENTINELS) & ~t.eq("NA")
    return series.isna() | t.eq("") | is_sentinel
```

---

### `qc/columns.py` (new module — normalisation + collision detection)

**Analog:** `qc/schema.py` for the Streamlit-free, sibling-import, pure-function shape; `qc/predicates.py` for the vectorised-function convention.

**Imports pattern** (mirror `qc/schema.py` lines 7-11):
```python
import pandas as pd

from .domain import MLOS_REQUIRED_COLS, TAKEOFF_REQUIRED_COLS
from .predicates import pct
from .results import register
```
`qc/columns.py` needs no `register()` call itself (S3 registers in `qc/schema.py`, per D-10 — "S3 is free; the Schema layer holds only S1 and S2"). It exposes pure functions consumed by `qc/schema.py` and by `app.py`'s load paths.

**Core pattern** — collision-before-rename (Established Fact 2), already fully worked out in 02-RESEARCH.md Pattern 3:
```python
import re

_WS_HYPHEN_RE = re.compile(r"[\s\-]+")
_REPEAT_UNDERSCORE_RE = re.compile(r"_+")

def normalize_name(col: str) -> str:
    c = col.strip().lower()
    c = _WS_HYPHEN_RE.sub("_", c)
    c = _REPEAT_UNDERSCORE_RE.sub("_", c)
    return c

def normalize_columns(df, original_names=None):
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
    rename_map = {o: normalize_name(o) for o in original if o not in collided_originals}
    renamed_df = df.rename(columns=rename_map)
    renames_applied = {o: n for o, n in rename_map.items() if o != n}
    return renamed_df, renames_applied, collisions
```
**Error handling pattern:** none needed beyond the collision-detection itself — this function never raises; a collision is reported as data (the `collisions` list), matching the codebase-wide convention of reporting failures as check dicts, not exceptions.

---

### `qc/mlos.py` (Rule 1 fix, R2/R3/R4 mask fix, +6 `.missing` registrations)

**Analog:** itself.

**`register()` call shape to replicate** (lines 23-55 — one line per identifier, in declaration order; new ids slot immediately after their sibling per Priority 3's disposition):
```python
register("2", "MLoS", "Takeoffpoint Name Match", "takeoffpoint in MLoS must match name in Takeoffpoint table")
```
New registrations (place `2.missing` right after `2`, `3.missing` after `3`, `4.missing` after `4`):
```python
register("2.missing", "MLoS", "Takeoffpoint — Blank", "takeoffpoint in MLoS must not be blank")
register("3.missing", "MLoS", "Takeoffpoint Code — Blank", "takeoffpoint_code in MLoS must not be blank")
register("4.missing", "MLoS", "Ward Code — Blank", "ward_code in MLoS must not be blank")
```
(Exact wording is the planner's/executor's call; identifiers `2.missing`/`3.missing`/`4.missing` are D-02-locked and must not change.)

**The `add()` closure** (lines 66-77) — every new check MUST go through this exact closure, unchanged:
```python
def add(num, rule, desc, mask, extra=None):
    n    = int(mask.sum())
    cols = BASE + [c for c in (extra or []) if c in mlos.columns and c not in BASE]
    checks.append({"Rule#": num, "QC Check": rule, "Description": desc,
                   "Failing Rows": n, "Total Rows": total,
                   "Fail %": pct(n, total),
                   "Status": "❌ FAIL" if n else "✅ PASS"})
    if n:
        sub = mlos[mask][cols].copy()
        sub.insert(0, "Rule#", num)
        sub.insert(1, "Rule", rule)
        details.append(sub)
```

**Rule 1 fix** — replace `.isnull()` (lines 91-92) with `vec_is_absent` across all `_NOT_NULL_COLS` (Research's Code Example, exact shape to copy):
```python
from .predicates import pct, vec_is_uuid, vec_is_editor, vec_is_absent
...
absent_frame = pd.concat(
    [vec_is_absent(mlos[c]) for c in _NOT_NULL_COLS], axis=1, keys=_NOT_NULL_COLS
)
_null_mask = absent_frame.any(axis=1)
```

**R2/R3/R4 fix — mask-exclusion pattern (Pattern 2, mandatory, not optional):** current code (lines 112-131) only fixes the *target* set; the corrected shape must ALSO exclude absent *source* cells to keep D-03's "exactly three checks" invariant:
```python
absent_source = vec_is_absent(mlos["ward_code"])
valid_targets = set(
    takeoff.loc[~vec_is_absent(takeoff["wardcode"]), "wardcode"].astype(str).str.strip()
)
not_matched = ~mlos["ward_code"].astype(str).str.strip().isin(valid_targets)
add("4", "Ward Code Match", "...", ~absent_source & not_matched, ["ward_code"])
add("4.missing", "Ward Code — Blank", "...", absent_source, ["ward_code"])  # D-07: unconditional
```
Apply the identical shape to rules 2 and 3.

**Error handling:** none — every rule is guarded on column presence (`if col in mlos.columns`), a convention that must be preserved unchanged (Research's "Established Patterns").

---

### `qc/takeoff.py` (TP2/TP3/TP4 mask fix, +3 `.missing` registrations)

**Analog:** itself, and mirrors `qc/mlos.py`'s fix (source/target swapped).

**Existing `register()`/`add()` shape** (lines 15-21, 32-43) — identical convention to `qc/mlos.py`, copy verbatim:
```python
register("TP2", "Takeoffpoint", "Name matches MLoS takeoffpoint",
         "name in Takeoffpoint must match takeoffpoint column in MLoS")
```
New: `TP2.missing`, `TP3.missing`, `TP4.missing` registered immediately after their siblings — **but per D-07, these three still emit only when the Takeoffpoint table exists** (this file already early-returns `if takeoff.empty or len(takeoff.columns) == 0: return [], pd.DataFrame()` at lines 25-26 — that guard covers all four TP-side checks including the new `.missing` trio, no change to that guard needed).

**Mask fix** (mirrors Pattern 2, lines 45-49 current shape):
```python
absent_source = vec_is_absent(takeoff["name"])
valid_targets = set(
    mlos.loc[~vec_is_absent(mlos["takeoffpoint"]), "takeoffpoint"].astype(str).str.strip()
)
not_matched = ~takeoff["name"].astype(str).str.strip().isin(valid_targets)
add("TP2", "Name matches MLoS takeoffpoint", "...", ~absent_source & not_matched, ["name"])
add("TP2.missing", "Name — Blank", "...", absent_source, ["name"])
```
Requires `from .predicates import pct, vec_is_uuid, vec_is_absent` (add `vec_is_absent` to the existing import line 12).

---

### `qc/schema.py` (+`S3` "Column Name Collision")

**Analog:** itself — `S1`/`S2`'s non-row-denominator precedent (lines 24-42).

**Pattern to copy** (S1's shape, lines 25-41 — a run-level check with a non-row `Total Rows`):
```python
mlos_cols    = set(mlos.columns.str.strip().str.lower())
missing_mlos = sorted(MLOS_REQUIRED_COLS - mlos_cols)
n_mlos_total = len(MLOS_REQUIRED_COLS)
n_mlos_miss  = len(missing_mlos)
checks.append({
    "Rule#": "S1", "QC Check": "MLoS Schema Alignment",
    "Description": f"{n_mlos_total - n_mlos_miss}/{n_mlos_total} required MLoS columns present",
    "Failing Rows": n_mlos_miss, "Total Rows": n_mlos_total,
    "Fail %": pct(n_mlos_miss, n_mlos_total),
    "Status": "❌ FAIL" if n_mlos_miss else "✅ PASS",
})
```
`S3` follows the same shape but sources its `collisions` list from `qc/columns.py`'s `normalize_columns()` (called upstream, before this check — collisions must be detected before the rename per Pattern 3, so `S3` is likely evaluated against a `collisions` argument passed into `run_schema_qc`, or `run_schema_qc` calls `normalize_columns` itself; either is consistent with this file's existing self-contained style). Register position: immediately after `S2` (line 14):
```python
register("S3", "Schema", "Column Name Collision", "Two or more original headers normalise to the same column name")
```
Per Research's Open Question #2 recommendation: `Failing Rows: 1, Total Rows: 1` binary framing for run-level S3/B4/B5 (or `len(collisions)`/collision-pair count — planner's call, follow whichever reads honestly per CONTEXT.md's discretion note).

---

### `qc/boundary.py` (+`B4` "Boundary Reference Fallback", `B5` "Boundary Reference Unavailable")

**Analog:** itself — B0's early-return-and-single-check shape (lines 40-48) is the direct analog for B5; the fallback site itself (lines 89-92) is where B4 detects the widening.

**B0's early-return pattern (analog for B5's early-return under D-19, "B4 emits nothing"):**
```python
if "ward_code" not in mlos.columns:
    checks.append({
        "Rule#": "B0", "QC Check": "Ward Code — Not Available on Data",
        "Description": "ward_code column is missing from the uploaded data — all boundary checks skipped",
        "Failing Rows": total, "Total Rows": total,
        "Fail %": "100.0%",
        "Status": "❌ FAIL",
    })
    return checks, pd.DataFrame()
```
B5's condition is `ref_df.empty` (not ward_code absence) — same early-return shape, appended near the top after B0's own check, then `return checks, pd.DataFrame()` before B1-B4 ever run (matching D-18: "only B0 runs").

**B4's detection site — the existing fallback** (lines 89-92, must be wrapped with a boolean flag rather than silently reassigning):
```python
_fallback_fired = filtered_ref.empty and not ref_df.empty
if filtered_ref.empty and not ref_df.empty:
    filtered_ref  = ref_df.copy()
    filtered_bbox = bbox_df.copy()
```
Then, using the `add()` closure already in this file (lines 53-64), unconditionally (D-17):
```python
if not ref_df.empty:
    n_state_wards = ... # count in the state's own filtered_ref before widening, for the PASS description
    add("B4", "Boundary Reference Fallback",
        "State reference had zero matching wards; B1 and B2 validated against the full national "
        "reference instead of the file's state" if _fallback_fired else
        f"Validated against {n_state_wards} ward(s) in the file's state",
        pd.Series([_fallback_fired] * total, index=mlos.index))
```
Register position (after `B3`, per D-16/Priority 3's canonical order B0..B5):
```python
register("B4", "Boundary", "Boundary Reference Fallback",
         "Whether B1/B2 validated against the file's state or fell back to the national reference")
register("B5", "Boundary", "Boundary Reference Unavailable",
         "No boundary reference file(s) were found — B1, B2, B3 and B4 could not run")
```

**Error handling:** none beyond existing column-presence guards; B4/B5 are additive checks riding the existing `(checks, details)` return-tuple signature (Research: "no signature change... every consumer picks it up for free").

---

### `app.py` — `get_uploaded_data` (D-12/D-13/D-14 session-state rewrite)

**Analog:** itself, lines 148-195 (the exact function to be edited).

**Current cache-key pattern to replace** (line 149):
```python
cache_key = (uploaded_file.name, getattr(uploaded_file, "size", None))
```
becomes (D-13, using stdlib `hashlib`, no new dependency):
```python
import hashlib
cache_key = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
```
**Session-state read/write pattern to replicate elsewhere** (lines 150-153, 190-195 — read-then-write-under-same-key convention, used verbatim for the two other call sites in D-13's table):
```python
if st.session_state.get("uploaded_cache_key") == cache_key:
    ...
    return st.session_state["mlos_df"], st.session_state["takeoff_df"]
...
st.session_state["uploaded_cache_key"] = cache_key
st.session_state["mlos_df"] = mlos_df
st.session_state["takeoff_df"] = takeoff_df
```
Per D-14, `mlos_df` here becomes **`mlos_raw`** (the normalised-but-uncorrected frame) — no bare `mlos_df` name may survive per D-15.

**Second/third cache-key call sites needing the same sha256 treatment** (sidebar submit, lines 561-565; main-body `_current_key`/`qc_cache_key`, lines 691-693, 721):
```python
tp_key = (uploaded_tp.name, getattr(uploaded_tp, "size", None)) if uploaded_tp else None
st.session_state["submitted_key"] = (
    uploaded.name, getattr(uploaded, "size", None), tp_key
)
```
becomes a `(sha256(mlos_bytes), sha256(tp_bytes) or None)` tuple (Research's Pattern 4 recommendation) at all three sites: `get_uploaded_data`'s own key, `submitted_key`, and `qc_cache_key`.

---

### `app.py` — one-snapshot guard (D-14/D-15)

**Analog:** itself, lines 741-747 (first auto-correct call, kept) and line 982 (second call, deleted).

**Pattern to keep, relabeled** (lines 741-747):
```python
st.write("🔧 Pre-step — Auto Correct")
mlos_df, _ac_log = qc.autocorrect.auto_correct_mlos(mlos_df)
```
becomes:
```python
st.write("🔧 Pre-step — Auto Correct")
mlos_corrected, _ac_log = qc.autocorrect.auto_correct_mlos(mlos_raw)
st.session_state["mlos_corrected"] = mlos_corrected
```
**Pattern to delete** (line 982 — this call site is removed entirely; downstream `corrected_df`/`build_corrected_excel` reads must be repointed to `st.session_state["mlos_corrected"]` instead of re-invoking `auto_correct_mlos`):
```python
corrected_df, correction_log = qc.autocorrect.auto_correct_mlos(mlos_df)  # DELETE — reuse cached mlos_corrected
```
**All five `run_*_qc` call sites** (lines 752, 762, 772, 786, 796) must read `mlos_corrected`, e.g.:
```python
schema_checks, schema_detail = qc.schema.run_schema_qc(mlos_df, takeoff_df)
```
→
```python
schema_checks, schema_detail = qc.schema.run_schema_qc(mlos_corrected, takeoff_df)
```
The **report's as-submitted sheet** is the sole permitted `mlos_raw` reader elsewhere in the file (D-14) — the AST guard in `tests/test_one_snapshot_guard.py` (below) enforces exactly this shape.

---

### `app.py` — sidebar rules-reference tables (+9 rows)

**Analog:** itself, lines 580-650 (five markdown tables, one per layer).

**Pattern to copy** — same `| Rule | Check |` markdown-table row shape, e.g. the existing MLoS table (lines 596-621):
```python
| 2 | takeoffpoint == takeoffpoint.name |
```
adds:
```python
| 2.missing | takeoffpoint must not be blank |
```
and similarly for `3.missing`, `4.missing` in the MLoS table; `TP2.missing`/`TP3.missing`/`TP4.missing` in the Takeoffpoint table (lines 633-641); `S3` in the Schema table (lines 580-592); `B4`/`B5` in the Boundary table (lines 642-650). `tests/test_rules_reference_matches_registry.py` asserts these tables agree with `qc.canonical_order()` — this is the acceptance test for this edit, not an optional cleanup.

---

## Shared Patterns

### Vectorised predicate convention
**Source:** `qc/predicates.py` lines 16-22 (`vec_is_uuid`, `vec_is_editor`)
**Apply to:** `vec_is_absent` (new), and every rule mask in `qc/mlos.py`, `qc/takeoff.py` that consumes it
```python
def vec_is_uuid(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(UUID_RE.pattern, na=False)
```

### `add()` closure (per-layer check + detail emission)
**Source:** `qc/mlos.py` lines 66-77 (identical copies exist in `qc/takeoff.py` lines 32-43 and `qc/boundary.py` lines 53-64)
**Apply to:** every new check in `qc/mlos.py`, `qc/takeoff.py`, `qc/boundary.py` — do not hand-roll a new check-dict shape; go through the existing closure in the file being edited.

### `register()` at import time
**Source:** `qc/results.py` lines 29-46, consumed identically in every layer module's top-level `register(...)` calls
**Apply to:** all 9 new identifiers (`2.missing`, `3.missing`, `4.missing`, `TP2.missing`, `TP3.missing`, `TP4.missing`, `S3`, `B4`, `B5`) — declaration order is emission order; place each immediately after its numeric/lettered sibling within its layer module.

### Relative sibling imports only (no `qc/__init__.py` round-trip)
**Source:** every existing `qc/*.py` file's own import block (e.g. `qc/predicates.py` line 10, `qc/schema.py` lines 9-11)
**Apply to:** `qc/columns.py` (new) and every edited layer file — `from .domain import X`, never `from . import domain` or `import qc; qc.domain.X` (Pitfall 5).

### AST-over-`app.py` structural guard
**Source:** `tests/test_no_streamlit_in_qc.py` lines 18-56 (`_find_ui_framework_imports`, `_scan_qc_directory`, the two guard tests built on them)
**Apply to:** `tests/test_one_snapshot_guard.py` (new) — parse `app.py` with `ast.parse`, walk the tree, assert every one of the five `run_*_qc` call sites, the on-screen table, and `build_corrected_excel`'s argument reference `mlos_corrected`, and that `mlos_raw` appears at exactly one call site (the as-submitted report sheet). Copy the "assert a real minimum count" defensive-test idiom (`test_guard_scanned_a_nonzero_number_of_files`) so the guard cannot pass by silently matching nothing.

### Plain-function, import-safe-without-pytest fixture builders
**Source:** `tests/fixtures.py` module docstring (lines 1-9) and `build_mlos_fixture`/`build_takeoff_fixture` (lines 116-238)
**Apply to:** `tests/golden_fixture.py` (new) — must remain a plain-function module with no pytest dependency, since `tests/baseline/capture_baseline.py` imports fixture builders directly outside a pytest session; the golden fixture's row-list should reuse `tests/fixtures.py`'s `_BASE_ROW`/`_row()` pattern rather than inventing a new row shape, translating a shared "logical blank" marker per format at write time (SQL `NULL` vs. `""`).

### Non-row denominator for run-level checks
**Source:** `qc/schema.py` `S1`/`S2` (lines 25-41) — `Failing Rows`/`Total Rows` counted over required-columns, not over MLoS rows
**Apply to:** `S3`, `B4`, `B5` — follow this precedent rather than defaulting to `len(mlos)`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tests/test_column_collision.py` | test | unit | No existing test constructs a bare, non-fixture-row-dict DataFrame with deliberately colliding headers; nearest partial precedent is `tests/test_registry_covers_emitted_ids.py`'s direct-call-with-hand-built-argument style (calls the QC function directly rather than only through the shared fixture). Use `pd.DataFrame({"Ward Code": [...], "ward_code": [...]})`-style inline construction; there is no richer analog to lift a shape from. |

## Metadata

**Analog search scope:** `qc/` (10 tracked files), `tests/` (13 tracked files + `tests/baseline/`), `app.py` (single-file monolith, sections 90-300, 500-1010, sidebar reference tables ~535-651)
**Files scanned:** `qc/mlos.py`, `qc/takeoff.py`, `qc/schema.py`, `qc/boundary.py`, `qc/autocorrect.py`, `qc/domain.py`, `qc/predicates.py`, `qc/results.py`, `qc/__init__.py`, `tests/fixtures.py`, `tests/test_no_streamlit_in_qc.py`, `tests/test_extraction_parity.py`, `tests/test_registry_covers_emitted_ids.py`, `app.py` (loaders, cache blocks, sidebar tables, autocorrect call sites)
**Tracked-source verification:** `git ls-files qc/ tests/` — all 20 files referenced as analogs above are tracked (confirmed non-empty `git ls-files` output for every path named); no `.gsd/capabilities/` or other gitignored mirror path is referenced anywhere in this document.
**Pattern extraction date:** 2026-09-10
