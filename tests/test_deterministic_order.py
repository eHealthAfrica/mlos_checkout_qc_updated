"""Cross-process determinism proof for rule emission order (ENGINE-09), and its structural
backstop (T-01-18).

Python fixes the string-hash seed once per process (``PYTHONHASHSEED``), so a same-process test
that imports ``qc`` and calls a layer function twice can never detect this defect — the seed is
already fixed for the whole test session before either call runs, and would pass just as readily
before the fix as after it (01-RESEARCH.md Pitfall 2, restating Pattern 3). The only valid proof
is a real subprocess restart with an explicit, differing hash seed per run.

Three seeds, not two, so a coincidental collision between two hash orderings cannot green this
test by accident. Every subprocess's stdout is compared as raw ``bytes``, never decoded text:
the printed check records carry non-ASCII characters (the ≤ sign in rule 9's description, the
❌/✅ status glyphs), and comparing at the byte level — after UTF-8 encoding, with no decode step
before the equality assertion — is what makes the "byte-identical" claim in this phase's success
criterion literally true rather than approximately true.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import qc

REPO_ROOT = str(Path(__file__).resolve().parent.parent)
HASH_SEEDS = ("0", "1", "42")

# Kept short and inline, per this task's own action text. Runs cwd-relative to REPO_ROOT (set via
# subprocess.run's cwd= below), so "tests" resolves to the real tests/ directory regardless of
# where this test file itself is invoked from.
_COLLECT = """
import sys
sys.path.insert(0, "tests")
import fixtures as f
import qc

mlos_df = f.build_mlos_fixture()
takeoff_df = f.build_takeoff_fixture()
ref_df, bbox_df = f.load_boundary_fixtures()

checks = []
c, _ = qc.schema.run_schema_qc(mlos_df, takeoff_df); checks += c
c, _ = qc.mlos.run_mlos_qc(mlos_df, takeoff_df); checks += c
c, _ = qc.settlement.run_settlement_qc(mlos_df); checks += c
c, _ = qc.takeoff.run_takeoff_qc(takeoff_df, mlos_df); checks += c
c, _ = qc.boundary.run_ward_boundary_qc(mlos_df, ref_df, bbox_df); checks += c
"""

_PRINT_RAW = _COLLECT + """
import json
print(json.dumps(checks, sort_keys=False))
"""

_PRINT_SORTED = _COLLECT + """
import json
checks = qc.sort_by_registry(checks)
print(json.dumps(checks, sort_keys=False))
"""


def _run_snippet(snippet: str, seed: str) -> bytes:
    """Fork a real subprocess with PYTHONHASHSEED explicitly set to seed, and return its raw
    stdout bytes, undecoded. A non-zero exit or anything on stderr is a test infrastructure
    failure, not a determinism finding, and is surfaced immediately rather than folded into a
    byte-mismatch assertion someone would have to debug blind."""
    env = {**os.environ, "PYTHONHASHSEED": seed}
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        env=env, cwd=REPO_ROOT, capture_output=True,
    )
    assert result.returncode == 0, (
        f"subprocess with PYTHONHASHSEED={seed!r} failed (exit {result.returncode})\n"
        f"stderr: {result.stderr.decode('utf-8', errors='replace')}"
    )
    return result.stdout


def _identifiers_from(stdout: bytes) -> list:
    """Decode only for a human-readable failure message — never for the equality assertion
    itself, which must compare undecoded bytes."""
    return [c["Rule#"] for c in json.loads(stdout.decode("utf-8"))]


def test_raw_emission_order_is_stable_across_hash_seeds():
    """Three subprocesses, each launched with a different explicit PYTHONHASHSEED, run all five
    QC layers against the fixture and print the raw check sequence — the emission order before
    any registry re-sort. The three outputs are byte-identical.

    This exercises the ordered-tuple half of the fix (qc/domain.py's YN_NA_COLS) on its own:
    before that conversion, this test would fail on the eight profile-flag identifiers, whose
    emission order tracked whatever order a set literal happened to iterate in for that
    process's particular hash seed."""
    outputs = [_run_snippet(_PRINT_RAW, seed) for seed in HASH_SEEDS]
    assert outputs[0] == outputs[1] == outputs[2], (
        f"raw check emission order differs across hash seeds {HASH_SEEDS!r}: "
        f"{[_identifiers_from(o) for o in outputs]!r}"
    )


def test_registry_sorted_order_is_stable_across_hash_seeds():
    """The same three subprocesses print the check sequence after every layer's checks pass
    through qc.sort_by_registry — the registry-imposed canonical order. The three outputs are
    byte-identical to each other, and the decoded identifier sequence equals canonical_order().

    This exercises the registry half of the fix on its own: it would hold even if the tuple
    conversion above were reverted, because sort_by_registry orders by each check's position in
    the registry, not by the order the check happened to be appended to the raw list — the
    structural backstop T-01-18 records."""
    outputs = [_run_snippet(_PRINT_SORTED, seed) for seed in HASH_SEEDS]
    assert outputs[0] == outputs[1] == outputs[2], (
        f"registry-sorted check emission order differs across hash seeds {HASH_SEEDS!r}: "
        f"{[_identifiers_from(o) for o in outputs]!r}"
    )

    expected_order = qc.canonical_order()
    actual_ids = _identifiers_from(outputs[0])
    assert actual_ids == expected_order, (
        f"registry-sorted identifier sequence diverges from canonical_order(): "
        f"actual={actual_ids!r} expected={expected_order!r}"
    )
