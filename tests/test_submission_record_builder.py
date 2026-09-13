"""Full record-contract tests for qc.submission_record.build_record (05-01 Task 3).

Every field D-02, D-03 and D-04 specify is pinned by an exact-value ``==`` assertion here,
rather than relying on the Task 2 tracer's single happy-path example. Synthetic ``QcSummary``
objects are built directly from ``qc.report.LayerSummary``/``QcSummary``, the same convention
``tests/test_layer_pass_rate.py`` uses -- no boundary reference CSVs, no Streamlit runtime, no
real QC engine run needed.

Each test's docstring says what would silently pass without its assertion, following
``tests/test_environment_pins.py``'s discipline.
"""

import json
import threading

import pandas as pd

import qc.report as report
import qc.submission_record as submission_record
from qc.results import canonical_order, get_rule
from datetime import datetime, timezone

# Real registered identifiers per layer, so summary.verdict_text (via QcSummary.n_fail's
# sort_by_registry call) can resolve every check's "Rule#" -- a synthetic, unregistered id would
# raise KeyError there, unrelated to anything this test is trying to prove.
_LAYER_IDS = {}
for _rid in canonical_order():
    _LAYER_IDS.setdefault(get_rule(_rid).layer, []).append(_rid)


def _checks(layer_name, n_pass, n_fail):
    ids = _LAYER_IDS[layer_name]
    assert n_pass + n_fail <= len(ids), (
        f"not enough registered {layer_name} ids for {n_pass} pass + {n_fail} fail"
    )
    pass_ids = ids[:n_pass]
    fail_ids = ids[n_pass:n_pass + n_fail]
    checks = [{"Rule#": r, "Status": "✅ PASS"} for r in pass_ids]
    checks += [{"Rule#": r, "Status": "❌ FAIL"} for r in fail_ids]
    return checks


def _default_layer(name):
    source_row_count = None if name == "Schema" else 10
    return report.LayerSummary(
        name=name,
        checks=_checks(name, 1, 0),
        detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS[name],
        source_row_count=source_row_count,
    )


def _summary(overrides=None):
    layers = {name: _default_layer(name) for name in report.LAYER_ORDER}
    if overrides:
        layers.update(overrides)
    return report.QcSummary(filename="kano_checkout.xlsx", layers=layers)


def _ts():
    return datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _file_identity(**kwargs):
    base = {"filename": "kano_checkout.xlsx", "sha256": "deadbeef"}
    base.update(kwargs)
    return base


# ─── Empty-checks layer still appears, not omitted ────────────────────────────────────────────

def test_takeoffpoint_layer_with_empty_checks_still_produces_present_zero_entry():
    """Without this, an unrun layer could be silently dropped from the record instead of
    appearing with zero checks -- the exact defect class D-02 names as a four-layer tool."""
    layers = {"Takeoffpoint": report.LayerSummary(
        name="Takeoffpoint", checks=[], detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS["Takeoffpoint"], source_row_count=0,
    )}
    summary = _summary(overrides=layers)
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert "Takeoffpoint" in record["layers"]
    assert record["layers"]["Takeoffpoint"]["checks_run"] == 0
    assert record["layers"]["Takeoffpoint"]["checks_failing"] == 0


# ─── Schema's distinct_issue_rows is always null ──────────────────────────────────────────────

def test_schema_distinct_issue_rows_is_none_even_with_nonempty_detail():
    """Without this, Schema's null-by-design distinct-row figure could accidentally become a
    real count once its detail frame is populated, contradicting D-02's literal source_row_count
    is not None rule."""
    layers = {"Schema": report.LayerSummary(
        name="Schema", checks=_checks("Schema", 0, 1),
        detail=pd.DataFrame({"Table": ["MLoS"], "Missing Column": ["set_target"]}),
        weight=report.LAYER_WEIGHTS["Schema"], source_row_count=None,
    )}
    summary = _summary(overrides=layers)
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["layers"]["Schema"]["distinct_issue_rows"] is None


# ─── checks_failing boundary cases ─────────────────────────────────────────────────────────────

def test_all_passing_layer_records_zero_checks_failing():
    """Without this, an off-by-one in the failing-count derivation could report a nonzero
    failure count for a layer where every check actually passed."""
    layers = {"MLoS": report.LayerSummary(
        name="MLoS", checks=_checks("MLoS", 5, 0), detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS["MLoS"], source_row_count=10,
    )}
    summary = _summary(overrides=layers)
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["layers"]["MLoS"]["checks_failing"] == 0


def test_all_failing_layer_records_checks_failing_equal_to_checks_run():
    """Without this, a layer where every check fails could report fewer failures than checks
    run, silently understating how bad the submission is."""
    layers = {"MLoS": report.LayerSummary(
        name="MLoS", checks=_checks("MLoS", 0, 4), detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS["MLoS"], source_row_count=10,
    )}
    summary = _summary(overrides=layers)
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["layers"]["MLoS"]["checks_failing"] == record["layers"]["MLoS"]["checks_run"] == 4


def test_one_failing_out_of_several_records_exactly_one():
    """Without this, an aggregate boolean 'any failing' could silently substitute for an exact
    count, which a `checks_failing == 1` assertion using truthiness alone would not catch."""
    layers = {"MLoS": report.LayerSummary(
        name="MLoS", checks=_checks("MLoS", 6, 1), detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS["MLoS"], source_row_count=10,
    )}
    summary = _summary(overrides=layers)
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["layers"]["MLoS"]["checks_failing"] == 1


# ─── distinct_issue_rows: zero rows is a real count, not absent ───────────────────────────────

def test_zero_row_source_table_records_zero_not_none():
    """Without this, a layer whose source table genuinely has zero rows could be conflated with
    a layer that has no source-row concept at all (Schema), reporting null instead of 0."""
    layers = {"MLoS": report.LayerSummary(
        name="MLoS", checks=_checks("MLoS", 1, 0), detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS["MLoS"], source_row_count=0,
    )}
    summary = _summary(overrides=layers)
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["layers"]["MLoS"]["distinct_issue_rows"] == 0
    assert record["layers"]["MLoS"]["distinct_issue_rows"] is not None


# ─── weighted_score / achievable_max: copied, float, JSON-stable ──────────────────────────────

def test_weighted_score_and_achievable_max_are_copied_floats():
    """Without this, the record could substitute a rounded or formatted-string value for the
    summary's own float, letting the record disagree with the verdict banner (D-02)."""
    summary = _summary()
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["weighted_score"] == summary.weighted_score
    assert record["achievable_max"] == summary.achievable_max
    assert isinstance(record["weighted_score"], float)
    assert isinstance(record["achievable_max"], float)


def test_score_of_zero_survives_json_round_trip():
    """Without this, a weighted_score of exactly 0.0 could be silently coerced to something
    JSON renders as an int or drops entirely, since 0.0 is falsy in a naive truthiness check."""
    layers = {name: report.LayerSummary(
        name=name, checks=_checks(name, 0, 1), detail=pd.DataFrame(),
        weight=report.LAYER_WEIGHTS[name], source_row_count=(None if name == "Schema" else 10),
    ) for name in report.LAYER_ORDER}
    summary = report.QcSummary(filename="f.xlsx", layers=layers)
    assert summary.weighted_score == 0.0
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    round_tripped = json.loads(json.dumps(record))
    assert round_tripped["weighted_score"] == 0.0


def test_score_equal_to_achievable_max_survives_json_round_trip():
    """Without this, a perfect achievable score could silently drift by a rounding step across
    the JSON round trip, breaking exact reconciliation against the verdict banner."""
    summary = _summary()
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["weighted_score"] == record["achievable_max"]
    round_tripped = json.loads(json.dumps(record))
    assert round_tripped["weighted_score"] == summary.weighted_score


# ─── officer_email edge cases ──────────────────────────────────────────────────────────────────

def test_officer_email_none_when_officer_is_none():
    """Without this, a missing officer (dev/unauthenticated session) could crash build_record
    instead of degrading gracefully to a null officer_email."""
    summary = _summary()
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["officer_email"] is None


def test_officer_email_none_when_officer_is_empty_dict():
    """Without this, an empty officer dict could raise a KeyError instead of producing a
    record with a null officer_email."""
    summary = _summary()
    record = submission_record.build_record(summary, {}, _file_identity(), "rid", _ts())
    assert record["officer_email"] is None


def test_officer_email_none_when_email_is_empty_string():
    """Without this, an officer dict carrying an empty-string email could produce a record with
    an empty-string officer_email instead of a proper null."""
    summary = _summary()
    officer = {"email": "", "name": "X", "domain": "example.com"}
    record = submission_record.build_record(summary, officer, _file_identity(), "rid", _ts())
    assert record["officer_email"] is None


def _walk_values(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_values(v)
    else:
        yield obj


def test_no_value_equals_officer_name_or_domain():
    """Without this, the officer's display name or domain could leak into the record, which
    D-01 deliberately excludes in favour of the email alone."""
    summary = _summary()
    officer = {"email": "officer@example.com", "name": "Distinctive Name Zzq", "domain": "example.com"}
    record = submission_record.build_record(summary, officer, _file_identity(), "rid", _ts())
    values = list(_walk_values(record))
    assert officer["name"] not in values
    # officer["domain"] legitimately appears as a substring of officer_email; check no *value*
    # in the record equals the domain outright.
    assert officer["domain"] not in values


# ─── takeoffpoint_file nested block ─────────────────────────────────────────────────────────────

def test_takeoffpoint_file_is_none_without_tp_filename():
    """Without this, a submission with no separately-uploaded Takeoffpoint file could still
    produce a spurious takeoffpoint_file block instead of null."""
    summary = _summary()
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert record["file"]["takeoffpoint_file"] is None


def test_takeoffpoint_file_present_with_both_fields():
    """Without this, a genuinely separately-uploaded Takeoffpoint file's identity could be
    silently dropped from the record instead of appearing as a two-key nested dict."""
    summary = _summary()
    fi = _file_identity(tp_filename="takeoff.csv", tp_sha256="cafebabe")
    record = submission_record.build_record(summary, None, fi, "rid", _ts())
    assert record["file"]["takeoffpoint_file"] == {"filename": "takeoff.csv", "sha256": "cafebabe"}


# ─── rename produces the same sha256 ────────────────────────────────────────────────────────────

def test_renamed_file_same_bytes_produces_equal_sha256_in_record():
    """Without this, a rename could be misread as a different file if the record derived
    identity from filename instead of the already-computed sha256."""
    summary = _summary()
    fi1 = _file_identity(filename="jan_submission.xlsx", sha256="samehash123")
    fi2 = _file_identity(filename="february_copy.xlsx", sha256="samehash123")
    r1 = submission_record.build_record(summary, None, fi1, "rid1", _ts())
    r2 = submission_record.build_record(summary, None, fi2, "rid2", _ts())
    assert r1["file"]["sha256"] == r2["file"]["sha256"]


# ─── determinism / no mutation ──────────────────────────────────────────────────────────────────

def test_identical_arguments_produce_equal_dicts_and_no_mutation():
    """Without this, build_record could hold hidden module state or mutate its arguments,
    producing a subtly different record on a second, identical call."""
    summary = _summary()
    officer = {"email": "officer@example.com", "name": "X", "domain": "example.com"}
    fi = _file_identity()
    fi_copy = dict(fi)
    officer_copy = dict(officer)
    r1 = submission_record.build_record(summary, officer, fi, "rid", _ts())
    r2 = submission_record.build_record(summary, officer, fi, "rid", _ts())
    assert r1 == r2
    assert fi == fi_copy
    assert officer == officer_copy


def test_concurrent_build_record_calls_return_equal_dicts_and_raise_nothing():
    """Without this, shared mutable module state in build_record could corrupt one thread's
    record with another's data under genuine concurrent QC runs."""
    summary = _summary()
    fi = _file_identity()
    results = []
    errors = []

    def worker():
        try:
            results.append(submission_record.build_record(summary, None, fi, "rid", _ts()))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, errors
    assert len(results) == 8
    assert all(r == results[0] for r in results)


# ─── layer key order always matches the registry, never a literal list ────────────────────────

def test_layer_key_order_equals_layer_order_read_at_test_time():
    """Without this, a hard-coded five-name list would keep passing if a sixth layer were added
    in a future phase and the record silently omitted it -- exactly the defect class D-02 names."""
    summary = _summary()
    record = submission_record.build_record(summary, None, _file_identity(), "rid", _ts())
    assert list(record["layers"]) == list(report.LAYER_ORDER)
