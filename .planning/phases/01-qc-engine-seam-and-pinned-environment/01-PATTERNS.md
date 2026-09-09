# Phase 1: QC Engine Seam and Pinned Environment - Pattern Map

**Mapped:** 2026-09-09
**Files analyzed:** 14 (6 new `qc/` modules besides the two `__init__.py`/`results.py` seam
files, 4 new `tests/` files, 1 modified `app.py`, 1 modified `requirements.txt`)
**Analogs found:** 14 / 14 — every new file's analog is the corresponding section of `app.py`
itself (this is a pure in-repo extraction, not a "borrow style from a sibling feature" task).
No file in this phase has zero analog since the source code being moved already exists.

**Note on this phase's nature:** every "new" file's pattern source is the *same* file
(`app.py`) it is extracted from — this is a mechanical seam-cutting phase, not new-feature work.
The planner's job is less "what should this look like" and more "cut exactly here, change
nothing else."

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `qc/results.py` | model/registry | event-driven (import-time registration) | *(no direct analog — net-new mechanism)*; closest existing convention: `FLAG_COLS` ordered list, `app.py:695-698` | new-pattern (research-specified) |
| `qc/domain.py` | config/constants | transform (pure data) | `app.py:98-108` (constant block) + `app.py:224-230` (`MLOS_REQUIRED_COLS`/`TAKEOFF_REQUIRED_COLS`) | exact (verbatim relocation) |
| `qc/predicates.py` | utility | transform | `app.py:207-216` (`pct`, `vec_is_uuid`, `vec_is_editor`) | exact (verbatim relocation) |
| `qc/schema.py` | service (rule engine) | CRUD-like validation / transform | `app.py:232-278` (`run_schema_qc`) | exact (verbatim relocation + id/registry wiring) |
| `qc/mlos.py` | service (rule engine) | transform | `app.py:805-965` (`run_mlos_qc`) | exact (verbatim relocation + id/registry wiring) |
| `qc/settlement.py` | service (rule engine) | transform | `app.py:539-633` (`run_settlement_qc`) | exact (verbatim relocation + id/registry wiring) |
| `qc/takeoff.py` | service (rule engine) | transform | `app.py:969-1012` (`run_takeoff_qc`) | exact (verbatim relocation + id/registry wiring) |
| `qc/boundary.py` | service (rule engine) | transform | `app.py:383-536` (`run_ward_boundary_qc`) | exact (verbatim relocation + id/registry wiring) |
| `qc/autocorrect.py` | service (transform) | transform (mutate-and-log) | `app.py:700-784` (`auto_correct_mlos`) | exact (verbatim relocation) |
| `qc/__init__.py` | facade/config | request-response (aggregation) | *(no direct analog)* — nearest structural precedent is the orchestration block at `app.py:1364-1426` that calls the five `run_*_qc()` functions in sequence | role-match |
| `app.py` (modified) | controller/UI (orchestration only) | request-response | itself, pre-edit — imports move to `from qc import ...`, call sites at `app.py:1364-1426` keep the same call shape | exact (this file is being pared down, not modeled on another) |
| `requirements.txt` (modified) | config | — | itself, pre-edit (4 unbounded lines) | exact |
| `tests/conftest.py` | test fixture | — | *(no test infra exists yet)* — fixture columns drawn from `MLOS_REQUIRED_COLS`/`TAKEOFF_REQUIRED_COLS`, `app.py:224-230` | new-pattern (research-specified) |
| `tests/test_results_registry.py` | test | event-driven (import-time assert) | research Code Examples section (verbatim pattern provided) | new-pattern (research-specified) |
| `tests/test_no_streamlit_in_qc.py` | test | batch (AST scan) | research Code Examples section (verbatim pattern provided) | new-pattern (research-specified) |
| `tests/test_deterministic_order.py` | test | batch (subprocess diff) | research Pattern 3 (verbatim pattern provided) | new-pattern (research-specified) |

## Pattern Assignments

### `qc/domain.py` (config, transform)

**Analog:** `app.py:98-108`, `app.py:224-230`

**Verbatim block to relocate** (`app.py:98-108`):
```python
VALID_DAY   = {"1","1_2","1_2_3","1_2_3_4","2","2_3","2_3_4","3","3_4","4","NA"}
VALID_YN_NA = {"Y","N","NA"}
VALID_YN    = {"Y","N"}
VALID_ACC   = {"Fully Accessible","Partially Accessible","Inaccessible"}
VALID_HAB   = {"Abandoned","Migrated","Inhabited","Partially Inhabited"}
UUID_RE     = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
EDITOR_RE   = re.compile(r'^[a-z]+\.[a-z]+$')
# Nullable MLoS fields (can be null — not subject to null checks):
# primarysettlement_name, alternate_name, reasons_for_inaccessibility
YN_NA_COLS  = {"highrisk","slums","densely_populated","hard2reach","border",
               "nomadic","riverine","fulani"}
```
**Required change per D-10/D-11:** `YN_NA_COLS` becomes a tuple, in this exact order (matches
D-01's `12.*` id ordering and `FLAG_COLS`'s existing convention):
```python
YN_NA_COLS = ("highrisk", "slums", "densely_populated", "hard2reach",
              "border", "nomadic", "riverine", "fulani")
```
Also relocate `FLAG_COLS` (`app.py:695-698`, already an ordered list — no change needed,
just move it here since `autocorrect.py` depends on it per D-07):
```python
FLAG_COLS = [
    "highrisk", "slums", "densely_populated", "hard2reach",
    "border", "nomadic", "scattered", "riverine", "fulani",
]
```
Also relocate `MLOS_REQUIRED_COLS` / `TAKEOFF_REQUIRED_COLS` (`app.py:224-230`) verbatim —
these are plain `set` literals used only for membership testing (`mlos_cols - MLOS_REQUIRED_COLS`),
not iteration order, so no tuple conversion is required here (only `YN_NA_COLS` is iterated
in the id-driving R12 loop and is in scope for D-10).

**Import needed at top of `qc/domain.py`:** `import re` (for `UUID_RE`/`EDITOR_RE`). No
`import streamlit` — this is exactly the file the ENGINE-05 guard test scans.

---

### `qc/predicates.py` (utility, transform)

**Analog:** `app.py:207-216`

**Verbatim block to relocate:**
```python
def pct(v, t): return f"{v/t*100:.1f}%" if t else "0%"

# Vectorized regex checks — avoid per-row Python function calls
def vec_is_uuid(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(UUID_RE.pattern, na=False)

def vec_is_editor(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(EDITOR_RE.pattern, na=False)
```
**Import needed:** `import pandas as pd` and `from .domain import UUID_RE, EDITOR_RE` (per
Pitfall 5 — sibling-to-sibling import, never via `qc/__init__.py`).

---

### `qc/results.py` (registry, event-driven — the seam itself)

**No codebase analog exists** — this is the one genuinely new mechanism in this phase. Use the
research's Pattern 1 verbatim (already vetted against D-01/D-10/D-12):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Rule:
    id: str
    layer: str
    name: str
    description: str

_REGISTRY: dict[str, Rule] = {}
_ORDER: list[str] = []

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
    return list(_ORDER)
```
No `pandas`/`streamlit` import — pure stdlib (`dataclasses`).

**Style note per project convention** (`CLAUDE.md` Code Style / Comments section): docstrings
on public functions, triple-quoted immediately after signature — add one to `register()` and
`canonical_order()` per the existing convention observed at `app.py:120-132`.

---

### `qc/schema.py` (service, transform) — `run_schema_qc`

**Analog:** `app.py:232-278`

**Full function to relocate verbatim** (only the two `checks.append({"Rule#": "S1"/"S2", ...})`
literals are candidates for wiring into the registry — ids `S1`/`S2` are frozen per D-04, no
change to the string values themselves):
```python
def run_schema_qc(mlos: pd.DataFrame, takeoff: pd.DataFrame):
    """
    Schema alignment QC — checks required columns are present.
    Returns check entries (same format as run_mlos_qc) and a detail DataFrame.
    Does NOT stop the QC process.
    """
    checks, details = [], []
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
    # ... (S2 block, identical shape) ...
    schema_detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return checks, schema_detail
```
**Registration block to add at top of `qc/schema.py`** (import-time, per Pattern 1):
```python
from .results import register
register("S1", "Schema", "MLoS Schema Alignment", "All required MLoS columns present")
register("S2", "Schema", "Takeoffpoint Schema Alignment", "All required Takeoffpoint columns present")
```
**Imports needed:** `import pandas as pd`, `from .domain import MLOS_REQUIRED_COLS, TAKEOFF_REQUIRED_COLS`,
`from .predicates import pct`, `from .results import register`.

**NOTE:** `build_schema_report_xlsx` (immediately below `run_schema_qc` in `app.py:280-296`)
is a report builder, not a QC engine — per D-06 it stays in `app.py`; do not move it into
`qc/schema.py`.

---

### `qc/mlos.py` (service, transform) — `run_mlos_qc` — the file requiring the identifier fix

**Analog:** `app.py:805-965` (160 lines, the largest and highest-risk relocation — see
Pitfall 1 in RESEARCH.md: verify `Failing Rows`/`Total Rows`/`Status`/detail-row contents are
byte-identical after the move for every rule except the renamed R11/R12 sub-checks).

**`add()` closure** (`app.py:816-828`) — relocate verbatim, unchanged; this is the per-file
pattern the registry does NOT replace within a single layer (only cross-layer id uniqueness is
centralized — `add()`'s job of building one check dict/detail-row stays local to each layer
function, per D-06's "relocate, don't rewrite" boundary):
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

**R11 loop — identifier fix only, logic and iteration unchanged** (`app.py:927-931`):
```python
# BEFORE (app.py:927-931) — bare "11" for all three fields, no ordering defect
# (list literal is already deterministic; only the id needs splitting)
for col in ["urban", "rural", "scattered"]:
    if col in mlos.columns:
        add("11", f"{col} is Y or N", ..., ~mlos[col]..., [col])

# AFTER — field-named ids per D-01
for col in ("urban", "rural", "scattered"):
    if col in mlos.columns:
        add(f"11.{col}", f"{col} is Y or N",
            f"{col} must be Y or N and must not be null",
            ~mlos[col].astype(str).str.strip().isin(VALID_YN), [col])
```
`11a`/`11b` blocks (`app.py:933-943`) relocate **verbatim, ids unchanged** — frozen per D-04.

**R12 loop — identifier fix + `YN_NA_COLS` now a tuple** (`app.py:945-949`):
```python
# BEFORE
for col in YN_NA_COLS:   # set literal — non-deterministic iteration order (F10)
    if col in mlos.columns:
        add("12", f"{col} = Y/N/NA", ..., ~mlos[col]..., [col])

# AFTER — YN_NA_COLS is now a tuple (qc/domain.py), ids field-named per D-01
for col in YN_NA_COLS:
    if col in mlos.columns:
        add(f"12.{col}", f"{col} = Y/N/NA",
            f"{col} must be Y, N, or NA",
            ~mlos[col].astype(str).str.strip().isin(VALID_YN_NA), [col])
```

**Registration block to add at top of `qc/mlos.py`** — reproduce D-01's ids verbatim, in this
exact order (registration order == emission order per D-12):
```python
from .results import register

register("1", "MLoS", "Required Fields — Not Null", "...")
register("2", "MLoS", "Takeoffpoint Name Match", "...")
register("3", "MLoS", "Takeoffpoint Code Match", "...")
register("4", "MLoS", "Ward Code Match", "...")
register("5", "MLoS", "Security Compromised Y/N", "...")
register("6", "MLoS", "Accessibility Status Valid", "...")
register("7", "MLoS", "Reason for Inaccessibility Required", "...")
register("8", "MLoS", "Habitational Status Valid", "...")
register("9", "MLoS", "set_target ≤ set_population", "...")
register("10", "MLoS", "number_of_household ≤ set_population", "...")
register("11.urban", "MLoS", "urban is Y or N", "...")
register("11.rural", "MLoS", "rural is Y or N", "...")
register("11.scattered", "MLoS", "scattered is Y or N", "...")
register("11a", "MLoS", "Cannot be both Urban and Rural", "...")
register("11b", "MLoS", "Urban cannot be Scattered", "...")
register("12.highrisk", "MLoS", "highrisk = Y/N/NA", "...")
register("12.slums", "MLoS", "slums = Y/N/NA", "...")
register("12.densely_populated", "MLoS", "densely_populated = Y/N/NA", "...")
register("12.hard2reach", "MLoS", "hard2reach = Y/N/NA", "...")
register("12.border", "MLoS", "border = Y/N/NA", "...")
register("12.nomadic", "MLoS", "nomadic = Y/N/NA", "...")
register("12.riverine", "MLoS", "riverine = Y/N/NA", "...")
register("12.fulani", "MLoS", "fulani = Y/N/NA", "...")
register("13", "MLoS", "Editor Format (firstname.surname)", "...")
register("14", "MLoS", "eha_guid is UUID", "...")
```
**Imports needed:** `import pandas as pd`, `from .domain import (VALID_ACC, VALID_HAB,
VALID_YN, VALID_YN_NA, YN_NA_COLS)`, `from .predicates import pct, vec_is_uuid, vec_is_editor`,
`from .results import register`.

---

### `qc/settlement.py`, `qc/takeoff.py`, `qc/boundary.py` (service, transform)

**Analogs:** `app.py:539-633` (SQ1-SQ4), `app.py:969-1012` (TP2-TP5), `app.py:383-536` (B0-B3).
Same relocation pattern as `qc/schema.py`/`qc/mlos.py`: verbatim function body, add an
import-time `register(...)` block at the top of the module reproducing the frozen ids exactly
(`SQ1, SQ2, SQ2b, SQ3, SQ4`; `TP2, TP3, TP4, TP5`; `B0, B1, B2, B3` — all D-04-frozen, no
suffix changes). `run_settlement_qc` uses `numpy` for the SQ4 haversine calculation
(`app.py:540` local import) — carry that local `import numpy as np` into `qc/settlement.py`
unchanged; do not hoist it to module level unless verified safe (no behavior change per phase
scope). `run_ward_boundary_qc` depends on the two bundled CSVs (`ward_boundary_ref.csv`,
`ward_boundary_bbox.csv`) — these stay loaded by the caller (`app.py`) and passed in as
`ref_df`/`bbox_df` params, exactly as the current signature already does; no path handling
moves into `qc/`.

---

### `qc/autocorrect.py` (service, transform) — `auto_correct_mlos`

**Analog:** `app.py:700-784`

**Excerpt (Correction 1, representative of the whole function's shape)**:
```python
def auto_correct_mlos(mlos: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Apply auto-corrections to the MLoS DataFrame.
    Returns a corrected copy and a log of changes made.
    """
    import uuid as _uuid
    df  = mlos.copy()
    log = []

    for col in FLAG_COLS:
        if col not in df.columns:
            continue
        mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
        n = int(mask.sum())
        if n:
            df.loc[mask, col] = "NA"
            log.append({"Column": col, "Correction": "NULL → NA", "Rows Fixed": n})
    # ... remaining 4 corrections, unchanged ...
    return df, log
```
**Move verbatim per D-09** — this function's own defects (F4 cache divergence, F5
non-deterministic GUIDs) are explicitly out of scope; do not "fix while moving."
**Imports needed:** `import pandas as pd`, `from .domain import FLAG_COLS`,
`from .predicates import vec_is_uuid` (if used elsewhere in the function body — verify against
full 700-784 range at implementation time, not just the excerpt above).

---

### `qc/__init__.py` (facade)

**No direct analog** — nearest structural precedent is the orchestration sequence at
`app.py:1364-1426` where `app.py` currently calls the five `run_*_qc()` functions one after
another and accumulates results. Per D-13 (Claude's Discretion in CONTEXT.md), the planner
chooses whether `__init__.py` exposes a `run_all()` façade or leaves `app.py` to import each
submodule directly. If a façade is chosen, use the research's registry re-sort helper as the
one new piece of logic here (not present anywhere in `app.py` today — this replaces implicit
per-process iteration order with the registry's explicit canonical order):
```python
from .results import canonical_order

def _sort_by_registry(checks: list[dict]) -> list[dict]:
    order_index = {rule_id: i for i, rule_id in enumerate(canonical_order())}
    return sorted(checks, key=lambda c: order_index[c["Rule#"]])
```
**Circular-import warning (Pitfall 5):** if `__init__.py` imports all five layer modules, none
of those layer modules may import anything from `qc` (the package) — only from sibling modules
directly (`from .domain import ...`), never `from qc import domain` (which re-triggers
`__init__.py`).

---

### `app.py` (modified — orchestration only)

**Analog:** itself, pre-edit. The call sites at `app.py:1364-1426` (not fully read in this
session but referenced by CONTEXT.md/RESEARCH.md line anchors) keep the same call shape —
`checks, detail = run_mlos_qc(mlos_df, takeoff_df)` becomes `checks, detail =
qc.mlos.run_mlos_qc(mlos_df, takeoff_df)` (or `qc.run_all(...)` if a façade is built). Remove
the relocated function bodies and the six symbol groups (`VALID_*`, `YN_NA_COLS`, `FLAG_COLS`,
`UUID_RE`/`EDITOR_RE`, `pct`, `vec_is_uuid`/`vec_is_editor`, `MLOS_REQUIRED_COLS`/
`TAKEOFF_REQUIRED_COLS`) from `app.py`; add `import qc` (or targeted submodule imports) at the
top instead. Loaders (`load_csv`, `load_xlsx`, `load_sqlite`, `get_uploaded_data`,
`app.py:104-204`) stay untouched per D-08.

**Sidebar rules-reference tables** (`app.py:1205-1279`, cited in CONTEXT.md but not re-read in
this session — treat as in-scope per D-01's Reversibility note) must be updated to show the new
`11.urban`/`11.rural`/`11.scattered`/`12.highrisk`...`12.fulani` identifiers alongside the
frozen 27, or the reference and the reports disagree.

---

### `requirements.txt` (modified)

**Analog:** itself, pre-edit:
```
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
xlrd>=2.0.1
```
**Target form** (per RESEARCH.md Standard Stack, all four bounded + numpy declared):
```
streamlit>=1.32.0,<2.0.0
pandas==3.0.5
numpy>=2.0.0,<3.0.0
openpyxl>=3.1.0,<4.0.0
xlrd>=2.0.1,<3.0.0
```
Add `pytest>=8.0.0,<10.0.0` either directly here or in a new `requirements-dev.txt` — planner's
call per Assumptions Log A3 in RESEARCH.md.

---

### `tests/*.py` (new — no analog, no test infra exists in this repo today)

Use the research's Code Examples verbatim as the starting point:
- `tests/test_results_registry.py` — duplicate-id rejection + full-ruleset-uniqueness test
  (RESEARCH.md "Duplicate-id rejection test" section, reproduced in full there).
- `tests/test_no_streamlit_in_qc.py` — AST-based guard scanning every `qc/*.py` file
  (RESEARCH.md "No-streamlit-import guard test" section, reproduced in full there).
- `tests/test_deterministic_order.py` — subprocess-pair test with differing `PYTHONHASHSEED`
  (RESEARCH.md Pattern 3, reproduced in full there). **Critical:** must spawn real subprocesses;
  an in-process double-call proves nothing (Pitfall 2).
- `tests/conftest.py` — minimal fixture `mlos_df`/`takeoff_df` DataFrames covering every column
  named in `MLOS_REQUIRED_COLS`/`TAKEOFF_REQUIRED_COLS` (`app.py:224-230`), ~5-10 rows, enough
  to exercise every rule id without building the full 3-format golden fixture (that's Phase 2's
  ENGINE-06 scope).

## Shared Patterns

### Column-presence guard (`if col in mlos.columns`)
**Source:** every rule across `app.py:232-1012` (e.g. `app.py:855` `if "takeoffpoint" in
mlos.columns and "name" in takeoff.columns:`)
**Apply to:** all five relocated `run_*_qc` functions — preserve every guard exactly; do not
add, remove, or reorder condition checks (silent-degradation-on-partial-file behavior is
frozen this phase, per RESEARCH.md's Established Patterns note — fixing it is Phase 2's
INTEG-03).

### Vectorized string normalization
**Source:** repeated throughout, e.g. `app.py:876-878`:
```python
~mlos["security_compromised"].astype(str).str.strip().isin({"Y", "N"})
```
**Apply to:** all relocated rule logic — `.astype(str).str.strip()` before any `.isin()`/regex
comparison. Never changed by this phase (no changed verdicts).

### `keep_default_na=False` on every load path
**Source:** `app.py:161-163`, `app.py:184-186` (both `load_csv` and `load_xlsx`)
**Apply to:** N/A for this phase (loaders stay in `app.py`, D-08) — noted here only so the
planner does not accidentally touch loader behavior while editing nearby import statements.

### Import-time registration (the one genuinely new shared pattern)
**Source:** RESEARCH.md Pattern 1 (`qc/results.py`)
**Apply to:** all five `qc/<layer>.py` modules — each declares its own `register(...)` calls at
module top level, executed once when `import qc` first imports that submodule.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `qc/results.py` | model/registry | event-driven | Net-new mechanism this phase introduces; no prior registry/rule-identity abstraction exists anywhere in `app.py`. Use RESEARCH.md Pattern 1 verbatim as the reference implementation instead of a codebase analog. |
| `qc/__init__.py` | facade | request-response | No prior package/façade exists (single-file app); RESEARCH.md's `_sort_by_registry` helper is the closest prior-art substitute. |
| `tests/*.py` (all four) | test | various | No test framework or test file exists anywhere in this repo (`TESTING.md`: "Framework: Not detected"); use RESEARCH.md's Code Examples section verbatim. |

## Metadata

**Analog search scope:** `app.py` (single-file monolith — the entire codebase's application
logic), confirmed via `git ls-files` that `app.py` and `requirements.txt` are tracked source
(no gitignored mirrors involved; no `.gsd/capabilities/` or plugin-synced trees exist in this
repo).
**Files scanned:** 1 (`app.py`, 1,962 lines — read via targeted `grep`+`sed` line-range extracts
per the large-file strategy: imports/constants block `1-230`, `run_schema_qc`/`build_schema_report_xlsx`
`232-296`, `FLAG_COLS`/`auto_correct_mlos` head `695-720`, `run_mlos_qc` full `805-965`; no
range re-read).
**Pattern extraction date:** 2026-09-09
