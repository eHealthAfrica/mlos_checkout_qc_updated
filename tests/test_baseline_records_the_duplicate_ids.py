"""Standing guard that tests/baseline/qc_baseline.json still describes the pre-fix state.

``qc_baseline.json`` is a FROZEN artifact, captured once from app.py before any of the six
relocating functions moved (see ``tests/baseline/capture_baseline.py``). These tests assert
facts about that frozen artifact, not about app.py's current code, and that is deliberate: they
must keep passing after Phase 1's identifier fix lands, because the baseline itself is never
regenerated after the fix. Their job is twofold — make it impossible to quietly re-capture the
baseline after the fix (which would erase the pre-state the whole extraction's parity argument
rests on), and record the F3 defect's exact size in a form later plans can measure against.

Do NOT "fix" these tests when app.py's rule identifiers change. A future identifier fix should
leave every test in this file passing, because it changes app.py, not this frozen JSON file.
"""

import json
from pathlib import Path

BASELINE_PATH = Path(__file__).resolve().parent / "baseline" / "qc_baseline.json"
BASELINE = json.loads(BASELINE_PATH.read_text())

LAYER_KEYS = ["schema", "mlos", "settlement", "takeoff", "boundary", "autocorrect"]


def test_baseline_covers_every_layer():
    """The JSON has all six layer keys, and each QC layer's checks list is non-empty. A
    baseline that recorded nothing would let every later parity comparison pass vacuously."""
    for key in LAYER_KEYS:
        assert key in BASELINE, f"baseline is missing the '{key}' layer key"

    qc_layer_keys = ["schema", "mlos", "settlement", "takeoff", "boundary"]
    for key in qc_layer_keys:
        checks = BASELINE[key]["checks"]
        assert len(checks) > 0, f"baseline layer '{key}' recorded zero checks"


def test_baseline_records_three_checks_numbered_11():
    """Exactly three checks in the mlos layer carry the identifier 11 (urban, rural and
    scattered each get their own Y/N check, all three sharing app.py's literal "11")."""
    mlos_checks = BASELINE["mlos"]["checks"]
    matching = [c for c in mlos_checks if c["Rule#"] == "11"]
    assert len(matching) == 3, (
        f"expected exactly 3 mlos checks numbered '11', found {len(matching)}: {matching}"
    )


def test_baseline_records_eight_checks_numbered_12():
    """Exactly eight checks in the mlos layer carry the identifier 12 (one per YN_NA_COLS
    member, all eight sharing app.py's literal "12")."""
    mlos_checks = BASELINE["mlos"]["checks"]
    matching = [c for c in mlos_checks if c["Rule#"] == "12"]
    assert len(matching) == 8, (
        f"expected exactly 8 mlos checks numbered '12', found {len(matching)}: {matching}"
    )


def test_baseline_has_more_emitted_checks_than_distinct_identifiers():
    """Across all five QC layers, 40 checks are emitted but only 31 distinct identifiers are
    used — the difference of 9 is the F3 collision (2 extra "11"s + 7 extra "12"s) recorded
    numerically, independent of which two rule families happen to collide."""
    qc_layer_keys = ["schema", "mlos", "settlement", "takeoff", "boundary"]
    all_rule_numbers = [
        check["Rule#"]
        for key in qc_layer_keys
        for check in BASELINE[key]["checks"]
    ]
    total_checks = len(all_rule_numbers)
    distinct_identifiers = len(set(all_rule_numbers))

    assert total_checks == 40, f"expected 40 emitted checks total, found {total_checks}"
    assert distinct_identifiers == 31, (
        f"expected 31 distinct identifiers, found {distinct_identifiers}: "
        f"{sorted(set(all_rule_numbers))}"
    )
    assert total_checks - distinct_identifiers == 9, (
        "expected the emitted-check count to exceed the distinct-identifier count by exactly "
        f"9 (the F3 collision), found a difference of {total_checks - distinct_identifiers}"
    )
