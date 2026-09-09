# Architecture Research

**Domain:** Rule-based geospatial data-validation tool (Streamlit + pandas), hosted, multi-user, brownfield single-file app growing to a package
**Researched:** 2026-09-09
**Confidence:** HIGH (module layout, caching, boundary enforcement — direct application of documented Streamlit/geopandas/huggingface_hub behavior to a codebase already read line-by-line) / MEDIUM (comparison to Great Expectations / pandera / soda-core internals — based on public docs and comparison articles, not their source trees)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  app.py — Presentation & Orchestration ONLY                          │
│  ┌────────────┐  ┌────────────────────┐  ┌─────────────────────┐    │
│  │ auth.py    │  │ Sidebar / 8 Tabs UI │  │ audit/               │    │
│  │ (OIDC/HF   │  │ Upload → Run QC     │  │ submission_log.py    │    │
│  │  identity) │  │ button, drilldowns  │  │ (append-only)        │    │
│  └─────┬──────┘  └──────────┬──────────┘  └──────────┬───────────┘    │
│        │ st.user            │ calls                  │ writes         │
└────────┼─────────────────────┼────────────────────────┼───────────────┘
         │                     ▼                        │
         │        ┌─────────────────────────┐           │
         │        │   qc/  (pure package)    │           │
         │        │  no `import streamlit`   │           │
         │        │  anywhere in this tree   │           │
         │        ├─────────────────────────┤           │
         │        │ loaders.py               │           │
         │        │ autocorrect.py           │           │
         │        │ results.py  (Rule +      │           │
         │        │   RuleResult registry)   │           │
         │        │ schema.py     (S)        │           │
         │        │ mlos.py       (MLOS)     │           │
         │        │ settlement.py (SQ)       │           │
         │        │ takeoff.py    (TP)       │           │
         │        │ boundary.py   (B)        │           │
         │        │ geometry.py   (GEO) NEW  │           │
         │        │ plausibility.py (POP) NEW│           │
         │        │ coverage.py   (COV) NEW  │           │
         │        │ scoring.py                │           │
         │        │ config.py  ← config/*.json│           │
         │        └────────────┬─────────────┘           │
         │                     │ (checks, details)        │
         │                     ▼                          │
         │        ┌─────────────────────────┐             │
         │        │ report/  (Excel, email)  │             │
         │        └────────────┬─────────────┘             │
         │                     ▼                          ▼
         │            UI display, downloads      HF Dataset repo (git)
         │                                        (private, append-only)
         ▼
  OIDC provider (HF OAuth / Google / etc.)
```

**Read the diagram as a dependency direction, not a call-order diagram:** arrows into `qc/` never originate from `auth.py` or `audit/`, and `qc/` never imports either. `app.py` is the only module that knows about all three.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `auth.py` | Resolve "who is this officer" once per session | Streamlit's native `st.login()` / `st.user` (OIDC, 1.42+) or HF Spaces' `hf_oauth: true` header injection — a thin wrapper, not a library |
| `qc/results.py` | Own the rule identifier scheme and the `RuleResult` record shape; the one place that knows what a "rule" is structurally | A frozen dataclass + a registry dict populated at import time, with a uniqueness assertion |
| `qc/<layer>.py` (8 files) | One pure `run_<layer>_qc(df, ..., config) -> (checks, details)` function per layer, unaware of Streamlit, auth, or storage | Plain functions using the shared `add()`-equivalent helper from `results.py` |
| `qc/config.py` | Load and validate `config/thresholds.json` into a typed object; fail loud on a bad value | `pydantic.BaseModel` (already lightweight, no new heavy dependency needed if avoided — `dataclasses` + manual checks also acceptable) |
| `qc/geometry.py` | Point-in-polygon against the ward polygon set; loads the polygon resource once | `geopandas.sjoin(points, wards, predicate="within")` against a `st.cache_resource`-cached `GeoDataFrame` |
| `report/` | Turn `(checks, details)` tuples into Excel workbooks and the SMTP email body | Same `build_excel_report`, `send_qc_email` logic, relocated, no logic change |
| `audit/submission_log.py` | Append one record per completed run to durable storage outside the ephemeral Space filesystem | `huggingface_hub.CommitScheduler` watching a local JSONL file, pushed to a private HF Dataset repo on an interval |
| `app.py` | Wire the above together per Streamlit rerun: check identity, load config, load data, call `qc`, render, log | Orchestration only — target is well under 400 lines once extraction is complete |

## Recommended Project Structure

```
mlos_checkout_qc/
├── app.py                      # UI + orchestration only (post-extraction)
├── auth.py                     # OIDC/HF identity wrapper; only module that touches st.user
├── qc/
│   ├── __init__.py             # re-exports run_all() and the RULES registry
│   ├── results.py              # RuleResult dataclass, Rule registry, add()-equivalent helper
│   ├── loaders.py               # load_sqlite/load_view/load_csv/load_xlsx/get_uploaded_data
│   ├── autocorrect.py           # auto_correct_mlos()
│   ├── config.py                 # load_config(), validated threshold model
│   ├── schema.py                 # S1-S2
│   ├── mlos.py                    # rules 1-14 (existing) — becomes MLOS-1..MLOS-14
│   ├── settlement.py              # SQ1-SQ4
│   ├── takeoff.py                  # TP2-TP5
│   ├── boundary.py                  # B0-B3 (reference CSV load stays here, @st.cache_data-free —
│   │                                  caching moves to app.py/loaders so qc/ stays Streamlit-free)
│   ├── geometry.py                   # NEW: GEO-1.. point-in-polygon layer
│   ├── plausibility.py                # NEW: POP-1.. population plausibility layer
│   ├── coverage.py                     # NEW: COV-1.. team/activity coverage layer
│   └── scoring.py                       # weighted score, _layer_pass_rate
├── report/
│   ├── excel.py                  # build_excel_report, build_schema_report_xlsx, build_corrected_excel
│   └── email.py                   # send_qc_email
├── audit/
│   └── submission_log.py           # append_submission(user, filename, verdict, score, ts)
├── config/
│   └── thresholds.json              # population + coverage thresholds, versioned in git
├── data/
│   ├── ward_boundary_ref.csv         # existing
│   ├── ward_boundary_bbox.csv        # existing
│   └── ward_polygons.geojson         # NEW, for geometry.py
└── tests/
    ├── conftest.py                    # golden fixtures, one per format (sqlite/csv/xlsx)
    ├── test_results_registry.py        # asserts every RuleResult id is globally unique
    ├── test_mlos_rules.py
    ├── test_boundary_rules.py
    ├── test_geometry_rules.py
    ├── test_plausibility_rules.py
    ├── test_coverage_rules.py
    └── test_no_streamlit_in_qc.py       # AST/grep guard: qc/ never imports streamlit
```

### Structure Rationale

- **`qc/` has no `import streamlit` anywhere** — this is the enforceable form of "the QC engine stays pure and unaware of identity." A five-line pytest that walks `qc/*.py` and asserts `"streamlit" not in ast.dump(tree)` (or a simple `grep -rl streamlit qc/` returning empty) is cheap, catches the boundary violation immediately in CI, and needs no interface/ABC ceremony.
- **One file per layer, not one file per rule.** At ~35 rules across 8 layers that's an average of ~4-5 rules per file — small enough to read in one sitting, matching the existing (and working) style where each `run_*_qc()` is one function with a handful of `add()` calls. A file-per-rule layout (35 files) would be over-engineering for a single-app tool with no plugin/third-party-rule use case.
- **`results.py` is the seam everything else is built against.** It must exist and be tested *before* the five existing layers are extracted, because extraction and the F3 identity fix are the same piece of work (PROJECT.md already scopes them together under M1).
- **`config/thresholds.json` lives in the repo, not in Space secrets.** Secrets are for credentials (SMTP, OIDC client secret); thresholds are business tuning values that benefit from being diffable, commented, and defaulted — a `git blame`-able JSON file under normal code review is the right amount of ceremony for "a wrong threshold is a settings edit, not a deploy" (see Pattern 2 below for why this still satisfies that constraint on Hugging Face Spaces).
- **`data/ward_polygons.geojson` sits beside the existing boundary CSVs**, not inside `qc/`, keeping the package itself free of large binary/data assets — `qc/geometry.py` takes a path or a pre-loaded `GeoDataFrame` as an argument, so tests can point it at a small fixture instead of the full 9,410-ward file.

## Architectural Patterns

### Pattern 1: Static Rule Registry (borrow the *idea*, not the machinery, from Great Expectations / soda-core / pandera)

**What:** Every check, in every layer, is registered as one `Rule` record (id, layer, name, description) at **module import time**, collected into a single `RULES: dict[str, Rule]` in `qc/results.py`. Each `run_<layer>_qc()` function still executes its checks as plain pandas code — nothing declarative or YAML-driven — but every `checks.append(...)` goes through one shared helper that looks the rule up by id, so the id, name, and description exist in exactly one place instead of being retyped at the call site (today's `add(num, rule, desc, mask, extra)` pattern is duplicated five times, per the codebase map's own "Redundant QC Check Pattern" finding).

**When to use:** Any time a rule set is large enough that "does this id already exist?" is a real question — true today at 27 rules with a documented collision (F3), more so at 35+.

**What to borrow vs. skip, concretely:**
- **Borrow (Great Expectations, soda-core):** the idea that a check's *identity* is a first-class, explicitly-declared value, not inferred from position or string-concatenation, and that identity is validated once centrally rather than trusted at each call site.
- **Borrow (pandera):** checks stay ordinary Python functions operating on `pd.Series`/`pd.DataFrame` — no need for pandera's own `Check`/`DataFrameSchema` objects; the existing vectorized-mask style already does what pandera's `Check` wrapper does, just without the wrapper.
- **Skip (Great Expectations):** the JSON "expectation suite" file format, the suite store/checkpoint abstraction, and the profiler — those exist because GE targets many teams sharing suites across many pipelines. This is one app maintained by one team; a Python module *is* the suite.
- **Skip (soda-core):** the SodaCL YAML DSL. Introducing a parallel rule-authoring language would fight the fact that most of these rules (cross-table matches, Haversine distance, regex format checks) are naturally pandas code, not declarative thresholds — a DSL would need an escape hatch back to Python for half the rule set anyway.
- **Skip (all of them) for this project:** plugin discovery (`entry_points`, `importlib.metadata`). Eight layers, statically known at development time, belong in one `qc/__init__.py` with eight explicit imports. Dynamic plugin loading solves "third parties can add rules without touching this repo," which is not a requirement here.

**Trade-off:** a shared registry adds one more file and one more indirection versus today's copy-pasted `add()` closures. That cost is worth paying once (at 27 rules, already past the point of comfortable copy-paste) and pays for itself immediately at 35+.

**Example:**
```python
# qc/results.py
from dataclasses import dataclass, field
from typing import Literal
import pandas as pd

@dataclass(frozen=True)
class Rule:
    id: str          # canonical, globally unique — e.g. "MLOS-1", "B-2", "GEO-1"
    layer: str        # "MLoS", "Boundary", "Geometry", ...
    name: str
    description: str

@dataclass
class RuleResult:
    rule: Rule
    failing_rows: int
    total_rows: int
    detail: pd.DataFrame

    @property
    def status(self) -> Literal["PASS", "FAIL"]:
        return "FAIL" if self.failing_rows else "PASS"

_REGISTRY: dict[str, Rule] = {}

def register(id: str, layer: str, name: str, description: str) -> Rule:
    if id in _REGISTRY:
        raise ValueError(f"Duplicate rule id: {id!r} (already registered for {_REGISTRY[id].layer})")
    rule = Rule(id, layer, name, description)
    _REGISTRY[id] = rule
    return rule
```
A single pytest (`test_results_registry.py`) that imports every `qc/*.py` module and then asserts `len(_REGISTRY) == len(set(_REGISTRY))` (trivially true given `register()`'s own guard, but importing all modules and asserting an expected *count* — e.g. "35 rules registered" — turns a silently-dropped rule into a failing test) is what actually closes F3 permanently, rather than relying on developer discipline the way the current five copy-pasted `add()` calls do.

### Pattern 2: Validated, Version-Controlled Threshold Configuration

**What:** `config/thresholds.json` (or `.yaml`) holds every numeric knob for the two new threshold-driven layers, grouped by layer. `qc/config.py` loads it once, validates it against an explicit schema, and raises a clear, specific error (not a stack trace) if a value is missing, the wrong type, or out of a sane range (e.g. a negative household size). The validated object — not the raw JSON — is what layer functions receive.

**When to use:** Any threshold that a non-engineer domain expert (a data officer or program lead) should be able to change without understanding the codebase, and any threshold explicitly called out as "a rule of thumb, not a published standard" (PROJECT.md's own framing for the population/coverage thresholds).

**Why this still satisfies "a settings edit, not a deploy":** On Hugging Face Spaces, editing a file in the repo does trigger a rebuild, same as editing `app.py` would. The constraint PROJECT.md states is about *risk surface*, not about avoiding git entirely: a JSON edit cannot introduce a logic bug, cannot break an unrelated rule, and can be reviewed by someone who doesn't read Python. That is the meaningful distinction between "settings edit" and "deploy" here — not whether git is involved. (If truly zero-git-touch tuning becomes a real requirement later, the same validated-config pattern moves the JSON into a Space "Variables" entry read via `os.environ`; the validation and typed-object layer stays identical either way — that migration is a loader change, not an architecture change.)

**Trade-off:** a schema-validated config is a few dozen extra lines over "just read the JSON and hope," but a wrong or missing threshold currently fails silently (defaults to `None`/`KeyError` deep inside a rule) versus failing loudly at startup with a message an officer or PM can act on.

**Example:**
```python
# qc/config.py
from pydantic import BaseModel, Field
import json

class PopulationThresholds(BaseModel):
    min_persons_per_household: float = Field(gt=0)
    max_persons_per_household: float = Field(gt=0)
    target_to_population_ratio_min: float = Field(ge=0, le=1)

class CoverageThresholds(BaseModel):
    max_settlements_per_team_per_day: int = Field(gt=0)

class ThresholdConfig(BaseModel):
    population: PopulationThresholds
    coverage: CoverageThresholds

def load_config(path: str = "config/thresholds.json") -> ThresholdConfig:
    with open(path) as f:
        return ThresholdConfig.model_validate(json.load(f))
```
(`pydantic` is already a plausible dependency for this size of app; if the project prefers zero new dependencies, the same shape works with `dataclasses` plus a hand-written `validate()` — the point is a typed object and a fail-fast load, not the specific library.)

### Pattern 3: Cache the Geometry Resource, Not the Geometry Data

**What:** Streamlit reruns the entire script top-to-bottom on every interaction. `st.cache_data` is the right tool for the existing `load_boundary_refs()` (two small CSVs, ~821 KB, cheap to copy on every cache hit, plain-DataFrame-hashable). It is the **wrong** tool for the ward polygon set: a `GeoDataFrame` with a built spatial index (`.sindex`, backed by an STRtree) is exactly the kind of "expensive, not-trivially-copyable resource" `st.cache_resource` exists for — Streamlit's own docs distinguish the two on precisely this axis (`cache_data` returns a fresh copy per call; `cache_resource` returns the same singleton object, appropriate for things like DB connections and loaded models). There is also a documented compatibility issue using `cache_data` with geopandas GeoDataFrames (spurious `CachedObjectMutationWarning`), which is avoided entirely by using `cache_resource` for this specific asset.

**When to use:** Any read-only, non-trivial-to-copy resource loaded once per process lifetime and reused across every rerun — the polygon set qualifies; the two boundary CSVs do not need to change caching strategy.

**Trade-off:** `cache_resource` objects are shared, mutable singletons across all sessions on the same Space container — safe here because the polygon layer is read-only after load (never mutated by a QC run), but this pattern would be wrong for anything the app writes back into.

**Example:**
```python
# qc/geometry.py
import streamlit as st          # NOTE: this import belongs in app.py's loader wrapper,
                                  # not inside qc/geometry.py itself — see the boundary
                                  # rule below. Shown together here only to illustrate
                                  # the caching call site.
import geopandas as gpd

@st.cache_resource(show_spinner="Loading ward polygons…")
def load_ward_polygons(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    _ = gdf.sindex   # force spatial index build once, at cache time, not per query
    return gdf

def run_geometry_qc(mlos: "pd.DataFrame", wards: gpd.GeoDataFrame) -> tuple[list, "pd.DataFrame"]:
    points = gpd.GeoDataFrame(
        mlos, geometry=gpd.points_from_xy(mlos["longitude"], mlos["latitude"]), crs=wards.crs,
    )
    joined = gpd.sjoin(points, wards, predicate="within", how="left")
    # rows where joined ward_code != mlos.ward_code, or index_right is NaN, are GEO-1 failures
    ...
```
**Boundary correction to the example above:** to honor "qc/ never imports streamlit," the `@st.cache_resource`-decorated loader should physically live in `app.py` (or a thin `qc/loaders.py` that is the one deliberate, documented exception, analogous to how `loaders.py` already needs to know about `st.cache_data` for the boundary CSVs today) and be **passed into** `run_geometry_qc(mlos, wards)` as a plain `GeoDataFrame` argument. `run_geometry_qc` itself takes no Streamlit dependency — it is handed an already-loaded resource, the same shape `run_ward_boundary_qc(mlos, ref_df, bbox_df)` already uses today for the CSV reference data. This is the existing codebase's own convention extended to the new layer, not a new one.

### Pattern 4: Identity and Audit as Edge Adapters, QC as the Core

**What:** `qc/` is the core: pure functions, DataFrames and a config object in, `RuleResult`s out. `auth.py` and `audit/submission_log.py` are edge adapters that `app.py` calls *around* the core, never *through* it. Concretely: `app.py` resolves `st.user` → gets an officer identity string; separately calls `qc.run_all(mlos, takeoff, wards, config)` → gets results with zero knowledge of who ran it; separately calls `audit.append_submission(user=officer, filename=..., verdict=..., score=..., timestamp=...)` after QC completes. The two edge calls compose in `app.py`; they never compose with each other or reach into `qc/`.

**When to use:** Any time "what happened" (the verdict) and "who did it, when, and where is that recorded" (the audit trail) have different lifecycles, different failure tolerances (a submission-log write failing should not block showing the officer their verdict), and — per this project's own stated constraint — different governance requirements (no passwords held; identity comes from OIDC only).

**Trade-off:** this is the lightweight version of hexagonal/ports-and-adapters architecture — real value at this scale, but stop there. Do **not** introduce formal `Protocol`/ABC interfaces for "an AuthProvider" or "an AuditSink" — there is exactly one implementation of each (HF/OIDC, HF Dataset repo) and one deployment target. Interfaces earn their cost when a second implementation is plausible; that is not the case here, and PROJECT.md explicitly rejects the scenario (an external managed DB) that would motivate one.

## Data Flow

### Request Flow (one Streamlit rerun, after a file is uploaded and "Run QC" is clicked)

```
Officer clicks "Run QC"
    ↓
app.py: st.user (identity already resolved at page load via auth.py)
    ↓
app.py: qc.loaders.get_uploaded_data(file)  →  mlos_df, takeoff_df
    ↓
app.py: qc.autocorrect.auto_correct_mlos(mlos_df) → corrected_df, correction_log
    ↓
app.py: qc.config.load_config()  →  ThresholdConfig            (cached: file rarely changes)
app.py: load_ward_polygons(path) → wards_gdf                    (st.cache_resource, loaded once)
app.py: load_boundary_refs()     → ref_df, bbox_df               (st.cache_data, existing)
    ↓
app.py: qc.run_all(corrected_df, takeoff_df, ref_df, bbox_df, wards_gdf, config)
    │      (pure — no streamlit, no identity, no I/O beyond the args it was given)
    ↓
    → list[RuleResult] across all 8 layers
    ↓
app.py: qc.scoring.weighted_score(results)  →  overall verdict + per-layer scores
    ↓
    ├──→ st.session_state cache (keyed on filename+size, existing pattern) → UI tabs render
    ├──→ report.excel.build_excel_report(results)  →  download button
    ├──→ report.email.send_qc_email(results)        →  optional SMTP send
    └──→ audit.submission_log.append_submission(user, filename, verdict, score, ts)
              → local JSONL buffer → CommitScheduler → private HF Dataset repo (async, on interval)
```

### Key Data Flows

1. **QC is a pure fold, not a pipeline of side effects.** Everything from "load" to "score" is data transformation with no external writes; the only writes (Excel bytes for download, SMTP send, audit log append) happen strictly after a verdict exists and are triggered by `app.py`, not by `qc/`. This is what makes the golden-fixture pytest suite possible: `qc.run_all(fixture_df, ..., config)` is fully deterministic and testable with no Streamlit runtime and no network.
2. **The audit write is fire-and-forget relative to the verdict shown to the officer.** `CommitScheduler` batches local file changes and pushes on an interval (not synchronously per submission) — appropriate given the append-only, "who checked what, when" nature of the log; a delayed or occasionally-retried push does not block or alter what the officer sees.
3. **Identity never flows into `qc/`.** `st.user` is read in `app.py`/`auth.py` and passed only to `audit.submission_log`, never as an argument to any `run_<layer>_qc()` function. This is the concrete, checkable form of "the QC engine should stay pure and unaware of identity" from the question — verifiable both by code review and by the `test_no_streamlit_in_qc.py` guard, since anything reading `st.user` necessarily imports `streamlit`.

## Scaling Considerations

This is a single private deployment for a bounded number of state data officers (dozens, not thousands), so the usual "0-1k / 1k-100k / 100k+ users" axis does not apply. The relevant scaling axes are **rule count** and **polygon/file size**, not concurrent users.

| Axis | Current | Growing to (M3) | Architecture response |
|------|---------|------------------|------------------------|
| Rule count | 27 across 5 layers | ~35+ across 8 layers | Registry pattern (Pattern 1) — catches collisions at test time regardless of count; file-per-layer stays readable well past 35 |
| Polygon set | 9,410 wards, bounding-box only (B2) | Same 9,410, true polygons | `st.cache_resource` + spatial index built once (Pattern 3) — the fixed cost is a one-time load per container lifetime, not per submission |
| Concurrent officers per Space container | Effectively 1 at a time in practice today | Possibly several simultaneous sessions once centrally deployed | `st.cache_resource` singletons are shared safely *because* the geometry/boundary data is read-only; if a future layer needed per-officer mutable state beyond `st.session_state`, that would need re-examination — not a concern for the layers scoped in M3 |
| Submission volume in the audit log | None today | One append per QC run, all officers, ongoing | `CommitScheduler`'s append-only, git-backed model degrades gracefully — git history grows, but the constraint sheet already rejects a queryable dashboard in favor of this simpler model until that requirement resurfaces |

### Scaling Priorities

1. **First likely bottleneck: Excel report build + geometry join on a large single-state file, both in one Streamlit process with ~16 GB RAM headroom (per the HF Spaces choice already made).** The geometry `sjoin` against 9,410 polygons is not the risk (sub-second even at large point counts with a spatial index); SQ4's proximity check and the styled Excel builder are the pre-existing memory-hungry steps this project's own audit already flagged — M3 should not make those worse, and `geometry.py` should reuse the same vectorized-pandas discipline the existing layers use rather than a naive per-row loop.
2. **Second: config drift between what `config/thresholds.json` says and what officers assume it says.** Mitigated by Pattern 2's schema validation plus rendering the active thresholds somewhere visible in the UI (e.g., an expander on the Plausibility/Coverage tabs) so a threshold edit is visibly reflected, not silently trusted.

## Anti-Patterns

### Anti-Pattern 1: A Full Plugin/DSL Framework for an Internal, Single-Team Rule Set

**What people do:** Reach for Great Expectations' suite-store model or a YAML rule DSL (SodaCL-style) because "that's how data quality tools are built," even when there's one repo, one team, and no third party ever adding a rule.
**Why it's wrong:** These frameworks solve *sharing and discovering* rules across many pipelines/teams. This project's actual problem (F3: two duplicate rule numbers across 11 checks) is solved by a 30-line registry with a uniqueness assertion, not by adopting an entire external framework's dependency surface and learning curve.
**Do this instead:** Pattern 1 above — a static Python registry, checked by one pytest, inside a package this team already owns end-to-end.

### Anti-Pattern 2: Reusing `st.cache_data` for the Polygon Layer Out of Habit

**What people do:** Copy the existing `@st.cache_data` pattern from `load_boundary_refs()` onto the new polygon loader because "that's what caching looks like in this codebase."
**Why it's wrong:** `st.cache_data` re-serializes/copies its return value on every cache hit. For two small CSVs that's free; for a `GeoDataFrame` carrying a built STRtree spatial index across ~9,410 polygons, it is wasted work every single rerun and has a documented compatibility rough edge with geopandas objects specifically.
**Do this instead:** `st.cache_resource` for the polygon `GeoDataFrame` (Pattern 3), keeping `st.cache_data` for the existing small, plain-DataFrame boundary CSVs — the two loaders should look different on purpose.

### Anti-Pattern 3: Letting `qc/` Read `st.user` "Just This Once" for Convenience

**What people do:** During the M2 auth work, pass `st.user` (or the officer's name) directly into a `run_*_qc()` function so it can be stamped onto detail rows or used in a message — a small, seemingly harmless shortcut.
**Why it's wrong:** It reintroduces exactly the coupling the question asks how to prevent, and it is very easy to do accidentally in a codebase whose current UI and logic already live in the same file. Once one layer function imports `streamlit` for identity, the "qc/ is pure" guarantee is gone for every consumer of that module, including the pytest golden-fixture suite, which now needs a Streamlit runtime to run at all.
**Do this instead:** Identity flows only through `app.py` → `audit.submission_log`. If a rule genuinely needs "submitted by," pass it as an explicit, anonymous-by-default argument (e.g., a `submitted_by: str | None` parameter) rather than reaching for `st.user` inside `qc/`, and cover the boundary with the static import-guard test.

### Anti-Pattern 4: Treating `config/thresholds.json` as Free-Form JSON

**What people do:** Read the config file with `json.load()` and pass the raw dict straight into rule functions, trusting that whoever edits the file gets every key and type right.
**Why it's wrong:** This is precisely the "wrong threshold is a deploy-time surprise" failure mode the constraint sheet is trying to avoid — a missing key surfaces as a `KeyError` deep inside a rule mid-run, on a specific state's file, not as a clear message when the Space restarts.
**Do this instead:** Pattern 2 — a validated, typed config object built once at startup, so a bad edit fails immediately and legibly.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OIDC provider (HF native OAuth or another provider) | Streamlit's built-in `st.login()` / `st.user` (1.42+), configured via `[auth]` in `secrets.toml` (`redirect_uri`, `cookie_secret`, provider client id/secret) | HF Spaces' native `hf_oauth: true` metadata flag is the lowest-friction path — no separate OAuth app registration or redirect URI management, and it matches the "no passwords stored by this application" constraint directly. This is the specific choice flagged as still-open in PROJECT.md; both paths integrate the same way at the `auth.py` boundary regardless of which is picked. |
| Hugging Face Hub — private Dataset repo | `huggingface_hub.CommitScheduler` watching a local append-only JSONL folder, pushed on an interval | Documented behavior: assumes append-only content in the watched folder; deleting/overwriting risks corrupting the repo. This matches the submission log's requirement exactly — never mutate a past entry, only add new lines/files. |
| SMTP | `smtplib`, credentials via Space secrets (already an M2 item independent of this question) | No architectural change from today beyond moving credentials out of the repo; `report/email.py` keeps the existing `send_qc_email()` logic. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `app.py` ↔ `qc/` | Direct function calls, plain Python objects (DataFrames, `ThresholdConfig`, `GeoDataFrame`) in; `list[RuleResult]` out | One-directional: `app.py` depends on `qc/`, never the reverse. Enforced by the "no `import streamlit` in `qc/`" test. |
| `app.py` ↔ `auth.py` | `auth.require_login()` at page top; `st.user` attributes read directly | `auth.py` is a thin wrapper (a handful of lines) around Streamlit's native auth, not a custom identity system. |
| `app.py` ↔ `audit/submission_log.py` | One function call after scoring completes: `append_submission(user, filename, verdict, score, timestamp)` | Failure isolation: a log-append error should be caught and surfaced as a non-blocking warning, not prevent the officer from seeing or downloading their verdict. |
| `qc/config.py` ↔ `config/thresholds.json` | File read + schema validation at load time | The only file-system dependency inside `qc/`; acceptable because it is data, not a Streamlit runtime dependency, and is trivially mockable in tests by pointing `load_config()` at a fixture path. |
| `qc/geometry.py` ↔ `data/ward_polygons.geojson` | Receives an already-loaded `GeoDataFrame` as an argument (loaded/cached by `app.py`/`qc/loaders.py`), never reads the path itself | Keeps `run_geometry_qc()` testable against a small in-memory fixture GeoDataFrame instead of the full 9,410-ward file. |

## Suggested Build Order

This restates the dependency shape underlying PROJECT.md's M1 → M2 → M3 sequencing, at the component level, for roadmap phase-splitting:

1. **`qc/results.py` (the registry + `RuleResult` shape) before any extraction.** This is the seam. Extracting the five existing layers into `qc/` and fixing F3 are the same change — there is no clean order where extraction happens first and identity gets fixed after, because "one shared helper instead of five copy-pasted `add()` closures" *is* the F3 fix.
2. **Extract the five existing layers + `autocorrect.py` + `loaders.py` into `qc/`, against the registry, with the golden-fixture pytest suite.** This is M1 as already scoped. Nothing in M2 or M3 should start before this exists, because both add to `qc/` and both want a test harness to add against.
3. **M2 (`auth.py`, `audit/submission_log.py`) and M3's `config.py` + `geometry.py` are mutually independent of each other** and can be built in either order or in parallel once step 2 lands — none of the four touches the other's files. PROJECT.md's stated preference is M2 before M3 for officer value sooner; that preference is a product-sequencing choice, not a technical dependency, and this research finds no architectural reason to override it.
4. **`config.py` (validated threshold loading) before `plausibility.py` and `coverage.py`.** Writing the two new threshold-driven layers against a typed, validated config object from the start avoids the churn of retrofitting validation onto rules that were written against raw dict access.
5. **`geometry.py` has no ordering dependency on `plausibility.py`/`coverage.py`** — it depends only on step 2 (the registry existing) and on the ward polygon file being in place (already confirmed available). It can be built in parallel with the threshold layers.
6. **`plausibility.py` and `coverage.py` last among the M3 layers**, both depending on step 4 (`config.py`) and step 1 (the registry), consistent with PROJECT.md's own note that threshold *values* are an open item still needed before M3 can be planned in detail.

## Sources

- [Streamlit — st.cache_data](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data) — HIGH confidence, official docs
- [Streamlit — st.cache_resource](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource) — HIGH confidence, official docs
- [Streamlit — Caching overview](https://docs.streamlit.io/develop/concepts/architecture/caching) — HIGH confidence, official docs
- [streamlit/streamlit GitHub issue #5934 — geopandas GeoDataFrame caching compatibility](https://github.com/streamlit/streamlit/issues/5934) — MEDIUM confidence, community-reported issue, corroborates the cache_resource recommendation for GeoDataFrames
- [Streamlit — st.login](https://docs.streamlit.io/develop/api-reference/user/st.login) — HIGH confidence, official docs
- [Streamlit — User authentication and information](https://docs.streamlit.io/develop/concepts/connections/authentication) — HIGH confidence, official docs
- [Streamlit — Authenticate users and personalize your app (tutorial)](https://docs.streamlit.io/develop/tutorials/authentication) — HIGH confidence, official docs
- [huggingface_hub — _commit_scheduler.py source](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/_commit_scheduler.py) — HIGH confidence, official source, confirms append-only assumption and periodic push behavior
- [Hugging Face Hub docs — Ingesting Datasets](https://huggingface.co/docs/hub/main/datasets-ingesting) — HIGH confidence, official docs
- [GeoPandas — sjoin reference](https://geopandas.org/docs/reference/api/geopandas.sjoin.html) — HIGH confidence, official docs, confirms `predicate="within"` for point-in-polygon and spatial index usage via `.sindex`
- [Spatial Join with GeoPandas (and GEOS) — architecture & performance](https://aetperf.github.io/2021/09/10/Spatial-Join-with-GeoPandas-and-GEOS.html) — MEDIUM confidence, third-party benchmark, corroborates spatial-index-backed `sjoin` performance at scale well beyond 9,410 polygons
- [Data validation in Python: a look into Pandera and Great Expectations](https://endjin.com/blog/a-look-into-pandera-and-great-expectations-for-data-validation) — MEDIUM confidence, third-party comparison article
- [pandera — Reading Third-Party (frictionless) Schema](https://pandera.readthedocs.io/en/latest/frictionless.html) — HIGH confidence, official docs, informs the "checks as plain Python functions, not a DSL" comparison
- [Soda Core — SodaCL optional check configurations (check identity vs. check ID)](https://docs.soda.io/sodacl-reference/optional-config) — HIGH confidence, official docs, source for the identity-vs-surrogate-id distinction used in the `RuleResult` design
- [Soda Core — GitHub repository](https://github.com/sodadata/soda-core) — HIGH confidence, official source
- Existing codebase, read directly: `/Users/BusayoFashoto/Desktop/4_april_26/4th_april_2026/git_clone/mlos_checkout_qc/app.py` and `.planning/codebase/ARCHITECTURE.md` — HIGH confidence, primary source

---
*Architecture research for: rule-based geospatial data-validation tool (Streamlit + pandas), M2/M3 additions*
*Researched: 2026-09-09*
