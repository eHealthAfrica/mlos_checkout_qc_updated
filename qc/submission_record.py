"""Pure submission-record builder and record-id/path minting, new for AUDIT-01/AUDIT-02
(D-02/D-03/D-04/D-14).

Pure module: no ``import streamlit``, no ``import huggingface_hub``, and no environment or
secrets access -- it takes only a ``QcSummary`` (``qc.report.QcSummary``), the officer dict from
``auth.current_officer()``, and a file-identity dict, and hands back a plain, JSON-serialisable
dict. Matches ``qc/mail_config.py``'s purity discipline: unit-testable with plain arguments, no
live session, no network.

Two alternatives were offered during discussion and rejected (D-02): the full per-check list and
a bare verdict-and-score record were both offered and not chosen -- the record carries a
per-layer checks-run/checks-failing/distinct-issue-rows summary instead. A later contributor
must not "improve" the record by expanding or shrinking its field set without bumping
``RECORD_SCHEMA`` -- the log is append-only, so every record ever written keeps this shape.
"""

import uuid
from datetime import datetime, timezone

from qc.report import LAYER_ORDER
from qc.version import VERSION

RECORD_SCHEMA = 1


def mint_record_id_and_path(ts=None):
    """D-14: mint a record id and its Dataset-repo path from one UTC instant.

    Returns ``(record_id, repo_path, ts)``. ``ts`` is timezone-aware UTC; when ``None``,
    ``datetime.now(timezone.utc)`` is used -- injecting ``ts`` is what makes the path's
    year/month partition testable. The caller must pass this same ``ts`` into ``build_record``,
    so a record's own ``timestamp_utc`` can never disagree with the month folder it sits in (a
    record minted in the last second of a month is the case that would otherwise split).

    Rejected alternatives (D-14): a flat folder, per-state folders, UUID-only names and
    sha256-led names were offered and not chosen -- the year/month partition keeps any one
    folder in the hundreds and listings sorted chronologically, and the compact-timestamp prefix
    plus a uuid4 suffix keeps two concurrent writers from ever colliding at one path.
    """
    if ts is None:
        ts = datetime.now(timezone.utc)
    stem = f"{ts.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex}"
    path = f"records/{ts.strftime('%Y')}/{ts.strftime('%m')}/{stem}.json"
    return stem, path, ts


def build_record(summary, officer, file_identity, record_id, ts, version=VERSION):
    """Project ``summary`` (``qc.report.QcSummary``), ``officer`` (``auth.current_officer()``'s
    dict, or ``None``) and ``file_identity`` into a plain, JSON-serialisable record dict.

    Never recomputes a verdict, score or layer count of its own -- ``verdict_text``,
    ``weighted_score`` and ``achievable_max`` are the summary's own attributes, copied straight
    across with no formatting, no rounding and no re-derivation. Mutates none of its arguments,
    so two QC runs building records at the same moment cannot interfere.
    """
    officer_email = None
    if officer and officer.get("email"):
        officer_email = officer["email"]

    layers = {}
    for name in LAYER_ORDER:
        layer = summary.layers[name]
        layers[name] = {
            "checks_run": len(layer.checks),
            "checks_failing": layer.n_fail,
            "distinct_issue_rows": (
                layer.distinct_issue_rows if layer.source_row_count is not None else None
            ),
        }

    takeoffpoint_file = None
    if file_identity.get("tp_filename") and file_identity.get("tp_sha256"):
        takeoffpoint_file = {
            "filename": file_identity["tp_filename"],
            "sha256": file_identity["tp_sha256"],
        }

    file_block = {
        "filename": file_identity["filename"],
        "sha256": file_identity["sha256"],
        "mlos_rows": summary.layers["MLoS"].source_row_count,
        "takeoff_rows": summary.layers["Takeoffpoint"].source_row_count,
        "takeoffpoint_file": takeoffpoint_file,
    }

    return {
        "record_schema": RECORD_SCHEMA,
        "app_version": version,
        "record_id": record_id,
        "timestamp_utc": ts.isoformat(),
        "officer_email": officer_email,
        "file": file_block,
        "verdict_text": summary.verdict_text,
        "weighted_score": summary.weighted_score,
        "achievable_max": summary.achievable_max,
        "layers": layers,
    }
