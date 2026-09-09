"""Standalone capture of app.py's QC engine functions, without importing app.py.

app.py's module body executes Streamlit UI code (``st.set_page_config``, ``st.markdown``, ...)
and its first import is ``streamlit``, none of which this script needs to compute QC results.
Instead this script parses app.py as text via ``ast``, extracts the named pure regions by AST
node name (never by hard-coded line numbers, so the extraction keeps working as later plans
move this code around), assembles them into a minimal module with only ``re`` and
``pandas as pd`` imported, ``exec``s that module into a fresh namespace, and runs the five
QC-layer functions plus ``auto_correct_mlos``'s correction log against the fixtures in
``tests/fixtures.py``.

The output, ``tests/baseline/qc_baseline.json``, is a FROZEN artifact: it records what app.py
produced before ANY of the six relocating functions moved. Do NOT regenerate it after an
extraction — regenerating it after the identifier fix erases the pre-fix record the whole
phase's parity argument rests on (see ``tests/test_baseline_records_the_duplicate_ids.py``).
"""

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_PY_PATH = REPO_ROOT / "app.py"
BASELINE_PATH = REPO_ROOT / "tests" / "baseline" / "qc_baseline.json"

# Module-level assignments the extracted module needs.
ASSIGNMENT_NAMES = [
    "VALID_DAY", "VALID_YN_NA", "VALID_YN", "VALID_ACC", "VALID_HAB",
    "UUID_RE", "EDITOR_RE", "YN_NA_COLS", "MLOS_REQUIRED_COLS",
    "TAKEOFF_REQUIRED_COLS", "FLAG_COLS",
]
# Function definitions the extracted module needs.
FUNCTION_NAMES = [
    "pct", "vec_is_uuid", "vec_is_editor", "run_schema_qc",
    "run_ward_boundary_qc", "run_settlement_qc", "auto_correct_mlos",
    "run_mlos_qc", "run_takeoff_qc",
]
ALL_NAMES = ASSIGNMENT_NAMES + FUNCTION_NAMES  # 20 names total


def extract_pure_regions() -> str:
    """Return assembled module source: ``import re`` + ``import pandas as pd``, followed by
    the source segments of every name in ALL_NAMES, sliced out of app.py's own text by AST
    node line ranges (``lineno``/``end_lineno``), in the order they appear in app.py.

    Raises RuntimeError naming any of the twenty required names not found at module level —
    a partial extraction must fail loudly, not silently produce a thinner baseline.
    """
    source = APP_PY_PATH.read_text()
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source, filename=str(APP_PY_PATH))

    found = {}
    for node in tree.body:
        name = None
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ASSIGNMENT_NAMES
        ):
            name = node.targets[0].id
        elif isinstance(node, ast.FunctionDef) and node.name in FUNCTION_NAMES:
            name = node.name

        if name is not None and name not in found:
            segment = "".join(lines[node.lineno - 1:node.end_lineno])
            found[name] = (node.lineno, segment)

    missing = [n for n in ALL_NAMES if n not in found]
    if missing:
        raise RuntimeError(
            f"extract_pure_regions: could not locate the following required name(s) as "
            f"top-level nodes in {APP_PY_PATH}: {missing}"
        )

    ordered_segments = [seg for _, seg in sorted(found.values(), key=lambda pair: pair[0])]
    header = "import re\nimport pandas as pd\n\n"
    return header + "\n".join(ordered_segments)


def _sorted_detail_records(detail) -> list:
    """Detail DataFrame -> list of record dicts, sorted by every column in order, so the
    baseline is byte-stable regardless of row-iteration order upstream."""
    if detail is None or detail.empty:
        return []
    records = detail.to_dict(orient="records")
    columns = list(detail.columns)
    return sorted(records, key=lambda r: tuple(str(r[c]) for c in columns))


def _layer(checks: list, detail) -> dict:
    checks_sorted = sorted(checks, key=lambda c: (c.get("QC Check", ""), c.get("Description", "")))
    return {"checks": checks_sorted, "detail": _sorted_detail_records(detail)}


def build_baseline() -> dict:
    """Exec the extracted module source, then run every QC layer against the RAW fixture (not
    the auto-corrected frame — ``auto_correct_mlos`` generates fresh UUIDs on every call, which
    would make rule 14's result differ between runs; that non-determinism is defect F5,
    Phase 2's concern, not this plan's). ``auto_correct_mlos``'s correction log is captured
    separately, since the log's Column/Correction/Rows Fixed triples are deterministic even
    though the corrected frame it also returns is not.
    """
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    from fixtures import build_mlos_fixture, build_takeoff_fixture, load_boundary_fixtures

    module_source = extract_pure_regions()
    namespace: dict = {}
    exec(compile(module_source, "<extracted_app_py>", "exec"), namespace)

    missing = [n for n in ALL_NAMES if n not in namespace]
    if missing:
        raise RuntimeError(f"build_baseline: exec did not define required name(s): {missing}")

    mlos = build_mlos_fixture()
    takeoff = build_takeoff_fixture()
    ref_df, bbox_df = load_boundary_fixtures()

    schema_checks, schema_detail = namespace["run_schema_qc"](mlos, takeoff)
    mlos_checks, mlos_detail = namespace["run_mlos_qc"](mlos, takeoff)
    settlement_checks, settlement_detail = namespace["run_settlement_qc"](mlos)
    takeoff_checks, takeoff_detail = namespace["run_takeoff_qc"](takeoff, mlos)
    boundary_checks, boundary_detail = namespace["run_ward_boundary_qc"](mlos, ref_df, bbox_df)

    _, autocorrect_log = namespace["auto_correct_mlos"](mlos)
    autocorrect_log_sorted = sorted(
        autocorrect_log, key=lambda entry: (entry.get("Column", ""), entry.get("Correction", ""))
    )

    return {
        "schema": _layer(schema_checks, schema_detail),
        "mlos": _layer(mlos_checks, mlos_detail),
        "settlement": _layer(settlement_checks, settlement_detail),
        "takeoff": _layer(takeoff_checks, takeoff_detail),
        "boundary": _layer(boundary_checks, boundary_detail),
        "autocorrect": {"log": autocorrect_log_sorted},
    }


def main() -> None:
    baseline = build_baseline()
    text = json.dumps(baseline, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    BASELINE_PATH.write_text(text)
    print(f"Wrote {BASELINE_PATH} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
