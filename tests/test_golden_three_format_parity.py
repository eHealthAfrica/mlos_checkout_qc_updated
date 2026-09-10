"""ENGINE-06's golden three-format harness: proves qc.schema.run_schema_qc,
qc.mlos.run_mlos_qc and qc.settlement.run_settlement_qc report an identical check summary for one
shared logical MLoS row list, whichever of .sqlite, .csv or .xlsx it arrived as. Bytes are built by
tests/golden_fixture.py and round-tripped through the real qc.loaders.load_submission — never
synthesised as frames directly, which is what makes this test capable of catching INTEG-01 at all.
"""

import qc
import golden_fixture as gf
from qc.loaders import load_submission

FORMATS = {
    "sqlite": ("golden.sqlite", gf.build_sqlite_bytes),
    "csv": ("golden.csv", gf.build_csv_bytes),
    "xlsx": ("golden.xlsx", gf.build_xlsx_bytes),
}


def _run_layers(mlos_df, takeoff_df) -> list:
    schema_checks, _ = qc.schema.run_schema_qc(mlos_df, takeoff_df)
    mlos_checks, _ = qc.mlos.run_mlos_qc(mlos_df, takeoff_df)
    settlement_checks, _ = qc.settlement.run_settlement_qc(mlos_df)
    return schema_checks + mlos_checks + settlement_checks


def _summarize(checks: list) -> dict:
    """Rule# -> (Failing Rows, Total Rows, Status). Fail % is excluded deliberately: it is a pure
    function of the first two through qc.predicates.pct and therefore follows by construction —
    comparing it too would only duplicate the Failing-Rows/Total-Rows comparison."""
    return {c["Rule#"]: (c["Failing Rows"], c["Total Rows"], c["Status"]) for c in checks}


def _emitted_order(checks: list) -> list:
    return [c["Rule#"] for c in checks]


def _load_all_formats() -> dict:
    rows = gf.build_shared_mlos_rows()
    cols = gf.MLOS_REQUIRED_COLS
    loaded = {}
    for fmt, (filename, builder) in FORMATS.items():
        payload = builder(rows, cols)
        uploaded = gf.FakeUploadedFile(payload, filename)
        loaded[fmt] = load_submission(uploaded, filename)
    return loaded


def _describe_divergence(fmt_a: str, summary_a: dict, fmt_b: str, summary_b: dict) -> str:
    """Name the specific diverging Rule# and the two formats that disagreed on it — a bare
    dict-inequality message would waste the whole point of this test."""
    keys = sorted(set(summary_a) | set(summary_b))
    lines = [
        f"Rule# {k}: {fmt_a}={summary_a.get(k)!r} vs {fmt_b}={summary_b.get(k)!r}"
        for k in keys
        if summary_a.get(k) != summary_b.get(k)
    ]
    return "; ".join(lines) if lines else "(no field-level divergence found)"


def test_three_formats_report_an_identical_check_summary():
    loaded = _load_all_formats()

    summaries = {}
    orders = {}
    for fmt, (mlos_df, takeoff_df) in loaded.items():
        checks = _run_layers(mlos_df, takeoff_df)
        summaries[fmt] = _summarize(checks)
        orders[fmt] = _emitted_order(checks)

    sqlite_summary = summaries["sqlite"]
    for fmt in ("csv", "xlsx"):
        assert summaries[fmt] == sqlite_summary, (
            f"{fmt} check summary diverged from sqlite: "
            f"{_describe_divergence(fmt, summaries[fmt], 'sqlite', sqlite_summary)}"
        )

    # A2: Total Rows equality across formats is guaranteed by construction (one shared row list)
    # — asserted explicitly here as a cheap sanity check rather than merely assumed.
    total_rows_by_format = {fmt: summary["1"][1] for fmt, summary in summaries.items()}
    assert len(set(total_rows_by_format.values())) == 1, (
        f"Total Rows diverged across formats even though all three encode the same shared row "
        f"list: {total_rows_by_format}"
    )

    # Non-vacuity: a golden test where every format agrees on zero findings would pass while
    # proving nothing. Rule 1 is the INTEG-01 regression sentinel — golden_fixture.py's shared
    # row list carries exactly one BLANK-marked _NOT_NULL_COLS cell (row "GoldenBravo"'s
    # timestamp), so Rule 1's Failing Rows must be exactly 1 in every format.
    for fmt, summary in summaries.items():
        failing, _total, _status = summary["1"]
        assert failing > 0, (
            f"{fmt}: Rule 1 Failing Rows is {failing}, not > 0 — a vacuous golden test"
        )
        assert failing == 1, (
            f"{fmt}: Rule 1 Failing Rows expected 1 (golden_fixture.py's one BLANK-timestamp "
            f"row), got {failing}"
        )

    # ENGINE-06's ordering edge: each format's emitted identifier order equals its own projection
    # of qc.canonical_order() (schema, then mlos, then settlement import order).
    canonical = qc.canonical_order()
    for fmt, order in orders.items():
        expected_order = [rule_id for rule_id in canonical if rule_id in order]
        assert order == expected_order, (
            f"{fmt}: emitted identifier order {order} does not match its canonical_order() "
            f"projection {expected_order}"
        )
