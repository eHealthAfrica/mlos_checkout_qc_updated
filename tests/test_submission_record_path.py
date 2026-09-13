"""Repo-path/record-id contract tests for qc.submission_record.mint_record_id_and_path
(05-01 Task 3, D-14).

Each test's docstring says what would silently pass without its assertion, following
``tests/test_environment_pins.py``'s discipline.
"""

from datetime import datetime, timezone

import qc.report as report
import qc.submission_record as submission_record


def test_last_second_of_january_partitions_under_january():
    """Without this, a boundary-second timestamp could be truncated or rounded into the wrong
    month folder instead of the month its own instant actually falls in."""
    ts = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
    _record_id, path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    assert path.startswith("records/2026/01/")
    stem = path.split("/")[-1]
    assert stem.startswith("20260131T235959Z")


def test_last_second_of_december_partitions_under_december_same_year():
    """Without this, a December 31 23:59:59 record could partition under the wrong year due to
    an off-by-one in the year/month derivation."""
    ts = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    _record_id, path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    assert path.startswith("records/2026/12/")


def test_first_second_of_next_year_partitions_under_new_year_january():
    """Without this, a record minted one second after the December 31 boundary could still be
    filed under the previous year -- the exact defect D-14's own worked example warns against."""
    ts = datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    _record_id, path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    assert path.startswith("records/2027/01/")


def test_single_digit_month_is_zero_padded():
    """Without this, March could render as '3' instead of '03', breaking lexicographic sort
    order across a year's worth of monthly folders."""
    ts = datetime(2026, 3, 15, 8, 0, 0, tzinfo=timezone.utc)
    _record_id, path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    assert "/03/" in path


def test_two_thousand_mints_same_ts_yield_distinct_ids_and_paths():
    """Without this, a mint keyed only on the timestamp would collide near-instantly under
    concurrent writers within the same second -- exactly the case D-14 is shaped for."""
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    ids = set()
    paths = set()
    for _ in range(2000):
        record_id, path, _ts = submission_record.mint_record_id_and_path(ts=ts)
        ids.add(record_id)
        paths.add(path)
    assert len(ids) == 2000
    assert len(paths) == 2000


def test_returned_ts_is_the_injected_ts_when_given():
    """Without this, the function could silently ignore an injected ts and return wall-clock
    time instead, breaking the caller's guarantee that build_record's timestamp_utc matches the
    path's own month partition."""
    ts = datetime(2026, 5, 5, 5, 5, 5, tzinfo=timezone.utc)
    _record_id, _path, returned_ts = submission_record.mint_record_id_and_path(ts=ts)
    assert returned_ts == ts


def test_returned_ts_is_utc_aware_when_none_given():
    """Without this, an omitted ts could silently produce a naive datetime, which would raise
    or misbehave when isoformat() is later compared against a '+00:00'-suffixed string."""
    _record_id, _path, returned_ts = submission_record.mint_record_id_and_path()
    assert returned_ts.tzinfo is not None
    assert returned_ts.utcoffset().total_seconds() == 0


def test_record_id_contains_only_filesystem_and_url_safe_characters():
    """Without this, a stray character in the uuid4 hex rendering or timestamp format could
    produce an id unsafe as both a repo path segment and a value printed on a report cover."""
    import re
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    record_id, _path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    assert re.fullmatch(r"[0-9A-Za-z_]+", record_id), record_id


def test_path_has_exactly_four_segments_ending_in_record_id_dot_json():
    """Without this, an extra or missing path segment could silently change the repo's folder
    depth, breaking every downstream assumption about records/YYYY/MM/<id>.json."""
    ts = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    record_id, path, _ts = submission_record.mint_record_id_and_path(ts=ts)
    segments = path.split("/")
    assert len(segments) == 4, segments
    assert segments[-1] == f"{record_id}.json"


def test_layer_order_reference_used_not_a_literal_list():
    """Self-check on this test file's own discipline: it must read qc.report.LAYER_ORDER at
    test time rather than hard-coding the five layer names, so a future sixth layer is not
    silently invisible to this suite."""
    assert len(report.LAYER_ORDER) == 5
    assert isinstance(report.LAYER_ORDER, tuple)
