# Phase 3: Verdict and Report Integrity - Pattern Map

**Mapped:** 2026-09-10
**Files analyzed:** 9 (3 new, 4 modified source, README, 5+ new tests grouped as one row)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `qc/report.py` (NEW) | service (Streamlit-free computation + report/email-body builders) | transform (checks/details → verdict/score/counts → workbook bytes / email text) | `qc/mlos.py` (module shape, docstring convention, `register()`-at-import pattern is N/A here but function/dataclass shape is) + `app.py:328-490` `build_excel_report`/`send_qc_email` (logic being relocated) | role-match (new kind of module, but codebase has an established "relocate business logic out of app.py into a Streamlit-free module" precedent from Phase 1 D-08/D-06) |
| `qc/results.py` (MODIFIED — add `get_rule(id)`) | utility (registry accessor) | request-response (id → Rule) | `qc/results.py:49-55` `canonical_order()` itself — extend same file, same fail-loud convention as `register()` | exact |
| `qc/takeoff.py` (MODIFIED — line 99, drop `ignore_index=True`) | service (QC layer) | CRUD/transform | `qc/mlos.py:268` and `qc/settlement.py:121` (`pd.concat(details)` without `ignore_index`) | exact — this is a one-line change to match an already-existing sibling pattern in the same codebase |
| `qc/boundary.py` (MODIFIED — line 188, drop `ignore_index=True`) | service (QC layer) | CRUD/transform | same as above | exact |
| `app.py` (MODIFIED — many presentation sites) | controller/UI (Streamlit orchestration) | request-response | itself; only site not diverging today is the pattern to copy toward (banner/email/Tab8 all already derive from `all_checks`) — cover (`:356-357,390-392`) is the site to fix to match the other three | exact (self-analog: 3 of 4 sites already correct, cover is the outlier) |
| `tests/test_report_workbook_shape.py`, `test_verdict_agreement.py`, `test_email_body.py`, `test_distinct_row_counting.py`, `test_layer_pass_rate.py`, `test_no_per_cell_styling.py`, `test_summary_sheet_order.py` (NEW) | test | request-response / structural-proof | `tests/test_no_streamlit_in_qc.py` (AST-over-`app.py`/`qc/` idiom), `tests/test_deterministic_order.py` (subprocess/registry-order proof), `tests/test_golden_three_format_parity.py` + `tests/fixtures.py` (fixture-builder reuse) | exact |
| `README.md` §8/§10/§11 | config/docs | — | itself (existing prose at `:247-275`, `:293-301`, `:305-325`) — rewrite in place | exact |

## Pattern Assignments

### `qc/report.py` (NEW — service, transform)

**Analog A — module docstring & import shape:** `qc/mlos.py:1-19` and `qc/takeoff.py:1-9`

```python
"""MLoS QC layer, relocated from app.py:720-880, with the R11/R12 identifier fix (D-01/D-02).
...
"""

import pandas as pd

from .domain import VALID_ACC, VALID_HAB, VALID_YN, VALID_YN_NA, YN_NA_COLS
from .predicates import pct, vec_is_uuid, vec_is_editor, vec_is_absent
from .results import register
```
Copy this shape for `qc/report.py`'s own docstring (explaining it is the Streamlit-free relocation target for `build_excel_report`/`send_qc_email`'s pure logic, per CONTEXT.md's Claude's Discretion note) and its imports (`from .results import canonical_order, get_rule`, `from . import sort_by_registry` via the package facade, `import pandas as pd`, `import openpyxl`, no `streamlit` import — this is exactly what `tests/test_no_streamlit_in_qc.py` will scan for).

**Analog B — dataclass convention:** `qc/results.py:17-22`

```python
@dataclass(frozen=True)
class Rule:
    id: str
    layer: str
    name: str
    description: str
```
Use this exact `@dataclass(frozen=True)` shape for `LayerSummary`/`QcSummary` (RESEARCH.md's Pattern 1 already gives the concrete fields — reuse verbatim, it was built against this analog).

**Analog C — score/verdict logic to relocate (source of truth for what to preserve):** `app.py:797-832`

```python
all_checks         = schema_checks + mlos_checks + settlement_checks + tp_checks + boundary_checks
n_fail              = sum(1 for c in all_checks if "FAIL" in c["Status"])
n_pass              = len(all_checks) - n_fail
...
LAYER_WEIGHTS = {
    "schema":     0.10,
    "mlos":       0.40,
    "settlement": 0.20,
    "tp":         0.20,
    "boundary":   0.10,
}

def _layer_pass_rate(checks):
    if not checks:
        return 1.0   # no checks → full credit (layer not applicable)   <-- F6, DO NOT COPY THIS BRANCH
    passing = sum(1 for c in checks if "FAIL" not in c["Status"])
    return passing / len(checks)
```
Port `LAYER_WEIGHTS` verbatim (keys/values unchanged — Deferred Ideas explicitly keeps weights as literals for this phase). Port the `"FAIL" in c["Status"]` / `sum(1 for c in checks if ...)` idiom verbatim — it is used at every counting site in the codebase and must stay consistent. **Do not port** the `not checks: return 1.0` branch — that is F6; `LayerSummary.pass_rate` must return `None` there per D-05/D-02 (RESEARCH.md Pattern 1 and Pitfall 2 give the exact fix shape).

**Analog D — workbook builder to relocate and reshape:** `app.py:328-490` (`build_excel_report`), specifically `write_summary` (`:398-416`), `write_detail` (`:419-443`), `write_raw` (`:446-456`), and the `hdr_row`/style-constant block (`:333-354`). Move the whole function (renamed/reshaped per D-06/D-07/D-09) into `qc/report.py`, keeping the style-constant block (`BLU`, `GRN`/`LGN`, `RED`/`LRD`, `LGY`, `hdr_fill`, `hdr_font`, `bdr`, `ctr`, `lft`) and `hdr_row` unchanged — D-09 only removes the per-*body-cell* style loop inside `write_detail`/`write_raw`, header rows and the Cover/Summary sheets keep exactly this styling.

**Analog E — plain-value body-row writing (ENGINE-08/D-09):** `app.py:310-324` (`build_corrected_excel`) is the one place in the codebase that already writes a bulk sheet without per-cell styling:

```python
def build_corrected_excel(df: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="MLoS Corrected")
        ws       = writer.sheets["MLoS Corrected"]
        hdr_fill = PatternFill("solid", fgColor="1D4ED8")
        hdr_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
        for ci, col in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(ci)].width = max(len(str(col)) + 4, 14)
    return out.getvalue()
```
This is the precedent for "styled header row, plain body, column widths only" — use `ws.append(row.tolist())` per RESEARCH.md's Pattern 4 for `write_detail`/`write_raw`'s new body loop, matching this file's header-only-styling convention.

**Analog F — email body/subject builder to extract as pure function:** `app.py:252-308` (`send_qc_email`), specifically the body-string f-string block (`:274-291`) and the verdict line (`:267`):

```python
n_fail  = sum(1 for c in all_checks if "FAIL" in c["Status"])
n_pass  = len(all_checks) - n_fail
verdict = "CLEAN ✅" if n_fail == 0 else f"FAILING ❌ ({n_fail} check(s))"
...
body = f"""MLoS QC Report — {filename}
{"="*60}
Overall Verdict   : {verdict}
Checks Run        : {len(all_checks)}
...
"""
for c in all_checks:
    body += f"[{c['Status']}] Rule {c['Rule#']}: {c['QC Check']} — {c['Failing Rows']} failing / {c['Total Rows']} ({c['Fail %']})\n"
```
Split into `qc/report.py::build_email_body(summary) -> tuple[str, str]` (body, subject) — pure, no `st.secrets`, no `smtplib` — reusing this exact f-string/loop shape but restructured per D-14 (one block per layer) and D-16 (subject carries verdict). The SMTP transport (`smtplib.SMTP`, `st.secrets.get(...)`, `MIMEMultipart`, `:293-308`) stays a thin wrapper in `app.py`.

---

### `qc/results.py` (MODIFIED — add `get_rule`)

**Analog:** `qc/results.py:49-55` (`canonical_order`) — same file, same fail-loud convention as `register()` (`:29-45`)

```python
def canonical_order() -> list[str]:
    """Return a copy of the registration-order identifier list.

    An empty registry returns an empty list, not ``None``, and this never raises.
    """
    return list(_ORDER)
```

Add immediately after, following `register()`'s own `raise ValueError(f"...{id!r}...")` fail-loud convention (`:38-42`):

```python
def get_rule(id: str) -> Rule:
    """Look up a registered Rule by its identifier. Raises KeyError naming the id if
    it was never registered — mirrors register()'s own fail-loud convention."""
    if id not in _REGISTRY:
        raise KeyError(f"No rule registered for id {id!r}")
    return _REGISTRY[id]
```
This is a two-line addition to an existing tracked file — no new module.

---

### `qc/takeoff.py` (MODIFIED — line 99) and `qc/boundary.py` (MODIFIED — line 188)

**Analog:** `qc/mlos.py:268` and `qc/settlement.py:121`

```python
# qc/mlos.py:268 — already correct, index preserved
return checks, pd.concat(details) if details else pd.DataFrame()
```

Apply the identical shape to the two D-11 sites:
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
One-line change per file; no other code in either file moves.

---

### `app.py` (MODIFIED — presentation sites: metrics bar, banner, Tab 2, Tab 8, email button)

**Analog:** itself. Three of the four current verdict derivations are already correct and are the pattern the fourth (cover, inside `build_excel_report`) must be brought into line with:

- Banner, already correct shape (`app.py:848-858`) — reads `n_fail` from `all_checks` (five-layer sum, `:801-802`)
- Generate Report tab verdict, already correct shape (`app.py:1223-1231`) — same `n_fail`
- Email verdict line, already correct shape (`app.py:265-267`) — same `n_fail` passed in as `all_checks`
- Report cover, the outlier (`app.py:356-357, 390-392`) — computes its own `total_fail` from only `mlos_checks`+`tp_checks`, which is F1

After introducing `qc/report.py`'s shared `QcSummary`, every one of these four sites should read `summary.verdict_text` / `summary.n_fail` instead of recomputing — replace the local `all_checks`-derived `n_fail` at each site with a single `summary = qc.report.build_summary(...)` call placed once at `app.py:797` (immediately after the cache if/else block resolves, per RESEARCH.md Pitfall 4 — never inside either branch alone), and have the metrics bar (`c1..c7`, `:837-843`), banner (`:848-858`), Tab 2 score table (`:872-897`), Tab 8 (`:1218-1297`), `build_excel_report`'s call site (`:1308-1311`) and `send_qc_email`'s call site (`:1327-1333`) all read from `summary` instead of the local variables they read today.

**Score-breakdown row shape to extend (D-02):** `app.py:893-898`

```python
score_rows = [
    {"QC Layer": "🔎 Schema Alignment",  "Weight": "10%", "Layer Pass Rate": f"{_layer_pass_rate(schema_checks)*100:.1f}%", "Weighted Contribution": f"{schema_score:.1f}%"},
    ...
    {"QC Layer": "🏆 Total", "Weight": "100%", "Layer Pass Rate": "—", "Weighted Contribution": f"{weighted_score:.1f}%"},
]
```
Keep this dict-list-of-rows shape; change the per-row `Layer Pass Rate` value to `"n/a"` when `summary.layers[k].pass_rate is None` (D-02) and `Weighted Contribution` to `"0.0%"` (a number, not `"n/a"`) in that case, and change the Total row's contribution string to the `72.0% of 80.0% achievable` template (D-01).

---

### Test files (NEW)

**Analog A — AST-over-`app.py`/`qc/` idiom:** `tests/test_no_streamlit_in_qc.py:1-45`

```python
QC_DIR = Path(__file__).resolve().parent.parent / "qc"
UI_FRAMEWORK = "streamlit"

def _find_ui_framework_imports(tree, framework=UI_FRAMEWORK) -> list[str]:
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == framework:
                    offenders.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == framework:
                offenders.append(node.module)
    return offenders
```
Reuse this exact `ast.walk` / `Import`/`ImportFrom` scan shape for the "four sites agree" structural test (`test_verdict_agreement.py`) — e.g. scan `app.py` for every site that constructs a verdict string or reads `n_fail`, and assert each reads it from the same `summary` object/attribute rather than recomputing (mirrors this file's "scan a directory, assert an offender set is empty" idiom).

**Analog B — subprocess/registry-order determinism proof:** `tests/test_deterministic_order.py:1-40` — reuse the same "collect checks via a short inline script run three times with different hash seeds, compare byte-for-byte" idiom for `test_summary_sheet_order.py`'s proof that the combined summary sheet's row order matches `canonical_order()` regardless of registration/hash order.

**Analog C — fixture builders:** `tests/fixtures.py` — `build_mlos_fixture()` (`:116`), `build_takeoff_fixture()` (`:214`), `load_boundary_fixtures()` (`:321`). The recommended shared Wave-0 fixture (Boundary-failing MLoS row + empty Takeoffpoint frame) is built by pairing `build_mlos_fixture()` with `pd.DataFrame()` for the takeoff side — mirror the existing empty-Takeoffpoint test pattern at `tests/test_extraction_parity.py:345-351`.

---

### `README.md` (MODIFIED — §8, §10, §11)

**Analog:** itself — `README.md:247-275` (§8 "Weighted QC Score", documents the `not checks → 1.0` full-credit rule at `:269`, which must be rewritten to D-01–D-05), `:293-301` (§10 "Generate & Download Report", sheet list must become D-06's nine/ten-sheet list), `:305-325` (§11 "Send QC Email", body/subject shape must become D-14/D-16). No external analog — rewrite these three sections in place to describe the new behavior, following the same prose-with-inline-code-block style already used throughout the file.

## Shared Patterns

### One Shared Computation, Four Readers (F1's structural fix)
**Source:** RESEARCH.md's Pattern 1 (`qc/report.py`'s `QcSummary`/`LayerSummary`), grounded in `qc/results.py:17-22`'s `@dataclass(frozen=True)` convention
**Apply to:** `app.py`'s metrics bar, banner, Tab 2, Tab 8, `build_excel_report`, `send_qc_email` — every site must read `summary.<attr>`, never recompute `n_fail`/verdict text locally. This is the single most important shared pattern in this phase; every presentation-site edit in `app.py` should be checked against it.

### `"FAIL" in c["Status"]` counting idiom
**Source:** `app.py:265, 356, 797, 821, 893` — repeated everywhere already
**Apply to:** `LayerSummary.n_fail` inside `qc/report.py` — keep this exact string-membership test rather than introducing an enum/constant, to stay consistent with every other counting site in the codebase that was not touched by this phase.

### Registry-order sort at the call site, never inside a layer
**Source:** `qc/__init__.py:26-33` (`sort_by_registry`) and its five existing call sites in `app.py` (`:737, 747, 757, 771, 781`, confirmed already correct by RESEARCH.md)
**Apply to:** the new combined `QC Summary` sheet's row ordering in `qc/report.py` — build it by iterating `canonical_order()` (or `sort_by_registry` over the union of all five layers' checks) and looking up each check by `Rule#`; do not add any new sort logic inside `qc/boundary.py`, `qc/takeoff.py`, etc.

### Styled header row / plain body rows for bulk sheets
**Source:** `app.py:310-324` (`build_corrected_excel`)
**Apply to:** `write_detail`/`write_raw` inside the relocated `qc/report.py` workbook builder (D-09/ENGINE-08) — style the header row only (`Font(bold=True)`, fill), then `ws.append(row.tolist())` per body row with zero per-cell style calls.

## No Analog Found

None — every file in scope has a concrete, closely-matching analog already in the tracked codebase (RESEARCH.md independently confirms no new library or architectural pattern is required).

## Metadata

**Analog search scope:** `app.py` (full file, 1-1344), `qc/` (all layer modules read in full), `tests/` (test_no_streamlit_in_qc.py, test_deterministic_order.py, fixtures.py), `README.md` §8/§10/§11
**Files scanned:** app.py, qc/results.py, qc/__init__.py, qc/mlos.py, qc/takeoff.py, qc/boundary.py, tests/test_no_streamlit_in_qc.py, tests/test_deterministic_order.py, tests/fixtures.py
**Pattern extraction date:** 2026-09-10
