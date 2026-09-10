# Phase 4: Central Deployment and Officer Identity - Pattern Map

**Mapped:** 2026-09-10
**Files analyzed:** 11
**Analogs found:** 8 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `qc/secrets_materializer.py` | utility | transform | `qc/columns.py` | role-match (pure, Streamlit-free, one small transform function) |
| `qc/auth_domain.py` | utility | transform | `qc/columns.py` | role-match (pure transform + validation predicate) |
| `auth.py` (new, repo root, thin Streamlit module) | middleware | request-response | `app.py` lines 261-271 (`load_boundary_refs`) + lines 274-308 (`send_qc_email`) | role-match (thin Streamlit wrapper around a pure helper, gate-before-render shape) |
| `app.py` (top-of-file materialiser call + `require_login()` gate insertion) | controller | request-response | `app.py` lines 1-40 (import/page-config block) | exact (same file, same insertion point) |
| `app.py::send_qc_email` (edit) | service | request-response | itself, `app.py:274-308` | exact |
| `requirements.txt` | config | batch | itself (existing file) | exact |
| Space README front-matter (new file, e.g. `README_HF.md` or Space repo) | config | file-I/O | none in repo (new artifact type) | no analog |
| `README.md` §Deployment (edit) | config | file-I/O | itself, `README.md` lines 340-376 | exact |
| `tests/test_auth_domain.py` | test | request-response | `tests/test_environment_pins.py` (pure-function unit-test shape) | role-match |
| `tests/test_secrets_materializer.py` | test | file-I/O | `tests/test_environment_pins.py` (reads a real file relative to repo root) | role-match |
| `tests/test_no_committed_secrets.py` | test | event-driven (static scan) | `tests/test_no_streamlit_in_qc.py` | exact (same AST-walk idiom, different target pattern) |
| `tests/test_auth_gate.py` / `test_auth_bypass_flag.py` / `test_refusal_page.py` / `test_smtp_recipients.py` | test | request-response | `tests/test_environment_pins.py` (env/config-driven behavior tests) | role-match |

## Pattern Assignments

### `qc/secrets_materializer.py` (utility, transform)

**Analog:** `qc/columns.py`

**Module docstring / purity framing pattern** (`qc/columns.py` lines 1-19):
```python
"""Column-name normalisation, new for INTEG-03/D-08/D-09/D-10.

Purely typographic: ... No semantic aliasing and no name is inferred from another name ...
"""

import re

import pandas as pd
```
Copy the shape, not the content: a docstring that (a) states what the function does NOT do
(no live env access at import time, no Streamlit dependency), (b) references the requirement
IDs (D-01, D-03) and the specific bug class it prevents (Streamlit issue #10543 — secrets
loaded before materialisation), matching `qc/columns.py`'s own "why this exists" framing.

**Core transform pattern** (`qc/columns.py` lines 22-30, function shape to mirror):
```python
def normalize_name(col: str) -> str:
    """Purely typographic column-name normalisation (D-08).
    ...
    Never raises — the empty string and a whitespace-only string both normalise to ...
    """
    c = col.strip().lower()
```
`build_secrets_toml(env: dict) -> str` should follow the same signature discipline: a plain
dict in, a plain string out, no `os.environ` read inside the pure function (env is injected),
matching `qc/columns.py`'s avoidance of any ambient state. The actual `os.environ.get(...)`
read and the `Path(...).write_text(...)` side effect belong in a thin wrapper (in `auth.py` or
at the top of `app.py`), not in this pure module — this mirrors how `app.py`'s
`load_boundary_refs` (below) keeps the file-existence check and I/O in the Streamlit-facing
layer while pure logic stays separate.

---

### `qc/auth_domain.py` (utility, transform)

**Analog:** `qc/columns.py`

**Validation predicate pattern** (`qc/columns.py`'s docstring on rejected approaches, lines 4-8):
```
a known-alias map (`wardcd` -> `ward_code`) was proposed during discovery and rejected,
because a wrong guess routes real data into the wrong rule.
```
Use the same "document the rejected alternative inline" convention for `is_authorized_domain`:
note that an allow-list was offered and rejected (D-04), so a future contributor does not
"simplify" the domain check back into one.

**Function signature discipline:** `extract_domain(user) -> str` and
`is_authorized_domain(domain: str, allowed: str = "ehealthnigeria.org") -> bool` should accept
a plain object/string, never `st.user` directly by type — mirrors `normalize_name(col: str)`
taking a plain string, never a DataFrame, keeping the function trivially testable with a fake.

---

### `auth.py` (middleware, request-response) — new thin Streamlit module at repo root

**Analog 1 (cached, existence-checked resource loader):** `app.py` lines 261-271
```python
@st.cache_data(show_spinner=False)
def load_boundary_refs():
    """Load ward code reference and bounding box lookup tables."""
    ref_df  = pd.read_csv(BOUNDARY_REF_PATH,  dtype=str, keep_default_na=False) if os.path.exists(BOUNDARY_REF_PATH)  else pd.DataFrame()
    ...
    return ref_df, bbox_df
```
Pattern to copy: guard on `os.path.exists`/env presence before acting, return a safe default
(empty DataFrame here; for `require_login()`, an explicit "unconfigured" branch) rather than
raising — matches D-03's requirement that missing `[auth]` config produces a clear message,
not an unhandled exception.

**Analog 2 (secrets read + thin sender):** `app.py` lines 274-308 (`send_qc_email`)
```python
def send_qc_email(summary):
    """Send QC summary email using SMTP credentials stored in st.secrets.
    Thin sender only ...
    """
    ...
    smtp_host = st.secrets.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(st.secrets.get("smtp_port", 587))
    smtp_user = st.secrets.get("smtp_user", "")
    smtp_pass = st.secrets.get("smtp_pass", "")
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        ...
```
Copy: (1) the docstring pattern that states "thin sender/gate only" and names which pure
module supplies the logic (`qc.report.build_email_subject_and_body` here → `qc.auth_domain`
for `require_login`), (2) `st.secrets.get(key, default)` read style — extend per RESEARCH.md's
DEPLOY-02 code example to also fall back to `os.environ.get(...)` since HF Spaces injects flat
env vars that `st.secrets` will not see. `require_login()` should read `GOOGLE_CLIENT_ID`,
`COOKIE_SECRET`, `MLOS_AUTH_DISABLED`, and the refusal-page contact address the same
env-then-secrets way.

**D-05 refusal-page pattern:** no exact analog exists (this codebase has no existing
"stop and show a message" UI branch outside `st.error()`/`st.stop()` in the loader). Use
`app.py`'s general `st.error(...)` + `st.stop()` idiom (seen at file-load error sites) as the
low-level primitive; the refusal page is new content, not a new mechanism.

---

### `app.py` (top-of-file insertion: materialiser + gate call)

**Analog:** `app.py` lines 1-40 (current top of file)
```python
import streamlit as st
import sqlite3
...
import qc
import qc.columns
import qc.report
from qc.domain import VALID_ACC, VALID_HAB, VALID_YN, VALID_YN_NA, YN_NA_COLS
from qc.loaders import (...)

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(...)
```
The materialiser call (`materialize_auth_secrets()` or equivalent from `auth.py`/
`qc/secrets_materializer.py`) must execute **before** `st.set_page_config(...)` — i.e. before
even the first import-adjacent `st.*` call in the existing file. The `require_login()` gate
call belongs immediately after the CSS `st.markdown` block and before the sidebar's
`with st.sidebar:` block (line 331 today), since D-09 requires every data-rendering `st.*`
call — including the sidebar reference tables — to sit behind the gate.

**Section-comment convention to follow** (seen throughout `app.py`):
```python
# ─── Page Config ────────────────────────────────────────────────────────────────
# ─── WHITE THEME CSS ────────────────────────────────────────────────────────────
```
Add `# ─── Auth Gate ──────────────────────────────────────────────────────────────`
as its own section, consistent with the em-dash banner convention (PROJECT.md Code
Organization).

---

### `app.py::send_qc_email` (service, request-response) — edit site

**Analog:** itself, `app.py:274-308` (see excerpt above)

**Change required per D-07 / RESEARCH.md DEPLOY-02 code example:**
```python
def get_recipients():
    """Returns (to_list, cc_list, error_message_or_None)."""
    to_raw = os.environ.get("SMTP_TO", "") or st.secrets.get("SMTP_TO", "")
    cc_raw = os.environ.get("SMTP_CC", "") or st.secrets.get("SMTP_CC", "")
    to_list = [a.strip() for a in to_raw.split(",") if a.strip()]
    cc_list = [a.strip() for a in cc_raw.split(",") if a.strip()]
    if not to_list:
        return [], [], "SMTP_TO is not configured — Send is disabled."
    return to_list, cc_list, None
```
Delete lines 286-289 (`TO = [...]`, `CC = [...]` literals) entirely; `send_qc_email` calls
`get_recipients()` and uses the returned lists in place of `TO`/`CC`. The Send button's
disabled state (D-07) is wired at the call site in the sidebar/tab UI, not inside
`send_qc_email` itself — follow the existing pattern where `send_qc_email` stays a pure-ish
"do the send" function and validation gating happens where the button is rendered.

---

### `requirements.txt` (config, batch)

**Analog:** itself (current file, 5 lines)
```
# pandas 3.0.5 requires Python >=3.11
streamlit>=1.32.0,<2.0.0
pandas==3.0.5
numpy>=2.0.0,<3.0.0
openpyxl>=3.1.0,<4.0.0
xlrd>=2.0.1,<3.0.0
```
Edit: bump `streamlit>=1.32.0,<2.0.0` → `streamlit[auth]>=1.42.0,<2.0.0` (or add a separate
`Authlib>=1.3.2` line if the extras syntax is not desired) per RESEARCH.md's Package
Legitimacy Audit. Preserve the existing comment-above-constraint convention (a `#` line
explaining a non-obvious pin, as with the `pandas 3.0.5` comment) — add one line noting *why*
the floor moved (`st.login`/`st.user` require >=1.42.0).

**Test analog for the bump:** `tests/test_environment_pins.py` already asserts pandas is
pinned exactly and numpy has both bounds; a `test_streamlit_floor_supports_auth` or extension
of this file should assert the streamlit line contains `>=1.42.0` and mentions `auth`, mirroring
`test_numpy_is_declared_with_both_bounds`'s string-assertion style exactly (split on
`>`/`<`/`=`, assert substrings present).

---

### Space README front-matter (config, file-I/O) — new file, no analog

No existing HF Space metadata file exists in this repo. RESEARCH.md's Recommended Project
Structure and Claude's Discretion section leave the file's location to the planner; there is
no in-repo pattern to copy from. Treat as new-artifact-type: front matter block
(`sdk: streamlit`, `python_version: "3.11"`, visibility public per D-09) with no analog file
to reference — planner should source the shape directly from HF's own documented front-matter
schema (cited in RESEARCH.md), not from an in-repo precedent.

---

### `README.md` §Deployment (config, file-I/O) — edit

**Analog:** itself, `README.md` lines 340-376 (current Streamlit Cloud section)
```markdown
SMTP credentials must be configured in Streamlit secrets:

```toml
smtp_host = "smtp.office365.com"   # or smtp.gmail.com for Gmail
smtp_port = 587
smtp_user = "your@email.com"
smtp_pass = "your-app-password"
```

...

## Streamlit Cloud

1. Fork or clone this repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Add SMTP credentials under **App secrets**
6. Deploy!
```
Rewrite the `## Streamlit Cloud` section as `## Hugging Face Spaces`, keeping the same
numbered-steps format, and extend the `toml`-fenced secrets block to a flat-env-var list
(`SMTP_TO`, `SMTP_CC`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `COOKIE_SECRET`,
`REDIRECT_URI`, plus existing `smtp_host`/`smtp_port`/`smtp_user`/`smtp_pass`), since HF
Spaces secrets are flat env vars, not a `.streamlit/secrets.toml` the officer edits directly.
Add the direct `*.hf.space` URL note (DEPLOY-04) and the 48-hour idle-sleep note in the same
numbered-list style.

---

### `tests/test_no_committed_secrets.py` (test, event-driven/static scan)

**Analog:** `tests/test_no_streamlit_in_qc.py` (full file read; AST-walk idiom)

**Structure to copy directly** (`tests/test_no_streamlit_in_qc.py` lines 1-45):
```python
"""Standing guard for the qc/ -> UI layer import boundary (ENGINE-05). ..."""

import ast
import subprocess
import sys
from pathlib import Path

QC_DIR = Path(__file__).resolve().parent.parent / "qc"
UI_FRAMEWORK = "streamlit"


def _find_ui_framework_imports(tree: ast.AST, framework: str = UI_FRAMEWORK) -> list[str]:
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


def _scan_qc_directory() -> "tuple[list[str], int]":
    offending_paths = []
    scanned = 0
    for path in sorted(QC_DIR.rglob("*.py")):
        scanned += 1
        tree = ast.parse(path.read_text(), filename=str(path))
        if _find_ui_framework_imports(tree):
            offending_paths.append(str(path))
    return sorted(offending_paths), scanned


def test_no_module_under_qc_imports_the_ui_framework():
    offenders, _scanned = _scan_qc_directory()
    assert not offenders, f"{UI_FRAMEWORK} imported in: {offenders}"


def test_guard_scanned_a_nonzero_number_of_files():
    """A guard that greens because it resolved an empty or mis-resolved directory reports
    confidence it never earned — assert a real minimum count of examined files."""
    _offenders, scanned = _scan_qc_directory()
    assert scanned >= 5, f"expected at least 5 files scanned under {QC_DIR}, found {scanned}"
```
Adapt: instead of AST-import-node scanning, walk `ast.Constant` (string) nodes across every
tracked `.py` file (scope: repo root + `app.py` + `qc/`, not just `qc/`) and assert none match
the four literal addresses from `app.py:286-289` (`adanna.alex@...`, `fashoto.busayo@...`,
`victor.idakwo@...`, `oluwadamilare.akindipe@...`) nor a generic secret-shaped pattern (e.g. a
40+ char token literal). Copy the "assert a nonzero scanned-file count" guard-of-the-guard
pattern verbatim — it is exactly reusable. Keep the module docstring's two-part framing
(what this proves, why a naive version would be insufficient).

---

### `tests/test_secrets_materializer.py`, `tests/test_auth_domain.py`, `tests/test_auth_gate.py`, `tests/test_auth_bypass_flag.py`, `tests/test_refusal_page.py`, `tests/test_smtp_recipients.py`

**Analog:** `tests/test_environment_pins.py` (full file read)

**Structure to copy:**
```python
"""<one-paragraph statement of why this standing test exists, referencing the requirement ID>"""

from pathlib import Path
...

REQUIREMENTS_PATH = Path(__file__).resolve().parent.parent / "requirements.txt"


def _read_requirement_lines():
    ...


def test_<specific_behavior_name>():
    """<docstring explaining what would silently pass without this specific assertion
    discipline, e.g. why an exact-match assertion beats a substring check>"""
    ...
```
Apply this to each new test file:
- `test_secrets_materializer.py`: pass a fake `env` dict into `build_secrets_toml`, assert the
  resulting TOML string contains a `[auth]` table with the expected keys; assert no-op (empty
  string or `None`) when `GOOGLE_CLIENT_ID` is absent, per RESEARCH.md's Pattern 1 code example.
- `test_auth_domain.py`: table-driven cases for `extract_domain`/`is_authorized_domain` using
  a small fake object (`SimpleNamespace(hd=..., email=...)`) — no live Streamlit session needed,
  matching the "injectable fake" note in CONTEXT.md's Claude's Discretion section.
- `test_auth_gate.py` / `test_auth_bypass_flag.py` / `test_refusal_page.py`: set/unset the
  relevant env vars (`MLOS_AUTH_DISABLED`, `GOOGLE_CLIENT_ID`) via `monkeypatch.setenv`, call
  `require_login()`-equivalent with mocked/caught `st.stop()`, assert the branch taken — same
  environment-variable-injection discipline `test_environment_pins.py` uses for `requirements.txt`
  parsing, applied to runtime behavior instead of a static file.
- `test_smtp_recipients.py`: table-driven `get_recipients()` cases (empty `SMTP_TO`, whitespace,
  multiple comma-separated addresses) — exact string-equality assertions, not substring checks,
  matching `test_pandas_installed_version_matches_the_pin`'s deliberate `==` framing.

## Shared Patterns

### Env-var-then-secrets read order (D-01, D-07, DEPLOY-02)
**Source:** RESEARCH.md Code Examples: DEPLOY-02 (derived pattern, not yet in codebase);
existing precedent for the "st.secrets.get with default" style at `app.py:294-303`
(`send_qc_email`'s `smtp_host`/`smtp_port`/`smtp_user`/`smtp_pass` reads).
**Apply to:** `auth.py`'s materialiser inputs, `get_recipients()`, and the refusal page's
contact-address read — every new secret this phase introduces should read
`os.environ.get(KEY, "") or st.secrets.get(KEY, "")` (env first, since HF Spaces injects flat
env vars that `st.secrets` does not see) rather than `st.secrets` alone.

### Gate-before-render / fail-closed-with-a-message (D-03, D-05, D-09)
**Source:** `app.py:261-271` (`load_boundary_refs`'s existence-check-then-safe-default shape)
and the project-wide convention (PROJECT.md Error Handling) of `st.error()` + `st.stop()` for
unrecoverable states.
**Apply to:** `require_login()` in `auth.py` — every branch (unconfigured+no-bypass,
signed-out, out-of-domain) must call `st.stop()` after rendering its message, never fall
through to the sidebar/uploader code that currently starts at `app.py:331`.

### AST/static standing-guard idiom (DEPLOY-02/DEPLOY-03 regression, ENGINE-05 precedent)
**Source:** `tests/test_no_streamlit_in_qc.py` (full file)
**Apply to:** `tests/test_no_committed_secrets.py` — reuse the module docstring framing,
the `_scan_qc_directory`-style helper (renamed and re-scoped to repo-wide `.py` files), and the
"assert nonzero files scanned" guard-of-the-guard test.

### Comment-banner section convention
**Source:** `app.py` throughout (`# ─── Section Name ───...`)
**Apply to:** the new `# ─── Auth Gate ───` section in `app.py`, and equivalent banners inside
`auth.py` if it grows multiple logical sections (materialiser call site, gate function, refusal
page renderer).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Space README front-matter (new metadata file) | config | file-I/O | No HF Space metadata file exists anywhere in this repo's history; this is a wholly new artifact type introduced by this phase. Source its shape from HF's own front-matter schema (cited in RESEARCH.md Sources), not an in-repo precedent. |
| `.planning/REQUIREMENTS.md` / `ROADMAP.md` / `PROJECT.md` wording edits (D-09) | docs | transform | Prose-editing task, not a code pattern; no code analog applies — treat as a straightforward find-and-replace of the "private" wording per D-09's exact replacement text in 04-CONTEXT.md. |
| `auth.py`'s refusal-page renderer (D-05) | component | request-response | No existing "authenticated but forbidden" UI branch exists anywhere in `app.py` today (only file-load-error `st.error()` sites); build from RESEARCH.md's Architecture Patterns diagram and D-05's plain-language spec, using `st.error()`/`st.stop()` as the only reusable primitive. |

## Metadata

**Analog search scope:** repo root (`app.py`, `requirements.txt`, `README.md`), `qc/`
(`columns.py`, `report.py`), `tests/` (`test_no_streamlit_in_qc.py`, `test_environment_pins.py`)
**Files scanned:** 6 read in full or targeted excerpt (`app.py` top-of-file + `send_qc_email` +
`load_boundary_refs`; `qc/columns.py` full; `qc/report.py` header; `tests/test_no_streamlit_in_qc.py`
full; `tests/test_environment_pins.py` full; `README.md` Deployment section); `requirements.txt` full
**Pattern extraction date:** 2026-09-10
