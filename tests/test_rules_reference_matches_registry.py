"""Standing proof that the in-app sidebar rules reference and the registry agree (T-01-20).

``app.py``'s sidebar renders five markdown reference tables — one each for Schema, MLoS,
Settlement, Takeoffpoint and Boundary — sharing the same two-column "Rule"/"Check" header. A
sixth expander ("Auto Correct Rules") documents corrections, not rule identifiers, and uses a
different three-column header ("# | Field | Correction Applied"); the parser below is scoped to
the "Rule"/"Check" header shape specifically so that table is excluded. Matching every
pipe-delimited row in the file instead would pull the Auto Correct table's correction numbers
("1", "1b", "2", "3", "4") in as if they were rule identifiers and produce a permanent false
failure, since none of those numbers are registered rule ids.

An identifier the engine emits but the reference omits leaves an officer without a definition for
a check they see fail in a report. An identifier the reference lists but the engine never emits
sends an officer looking for a check that does not run. Both are the same failure of trust
(T-01-20) and this file asserts against both directions.
"""

import re
from pathlib import Path

import qc

APP_PY_PATH = Path(__file__).resolve().parent.parent / "app.py"

# The exact two-column header shape shared by the five rule-identifier reference tables. The
# Auto Correct table's header ("# | Field | Correction Applied") does not match this pattern.
_HEADER_RE = re.compile(r"^\|\s*Rule\s*\|\s*Check\s*\|\s*$")
_SEPARATOR_RE = re.compile(r"^\|[-\s]+\|[-\s]+\|\s*$")
_ROW_RE = re.compile(r"^\|([^|]*)\|")


def parse_reference_tables(source: str) -> "list[list[str]]":
    """Return one list of identifiers per "Rule"/"Check"-headed markdown table found in
    ``source``, in the order the tables appear. A table's identifier list is read from the
    first cell of every row immediately following its header and separator rows, stopping at
    the first line that is not itself a pipe-delimited table row (a blank line or trailing
    prose)."""
    lines = source.splitlines()
    tables: "list[list[str]]" = []
    i = 0
    n = len(lines)
    while i < n:
        if _HEADER_RE.match(lines[i].strip()) and i + 1 < n and _SEPARATOR_RE.match(lines[i + 1].strip()):
            ids: "list[str]" = []
            j = i + 2
            while j < n:
                stripped = lines[j].strip()
                if not stripped.startswith("|"):
                    break
                match = _ROW_RE.match(stripped)
                if match:
                    ids.append(match.group(1).strip())
                j += 1
            tables.append(ids)
            i = j
        else:
            i += 1
    return tables


def test_reference_table_parser_found_all_five_tables():
    """The parser must find exactly the five rule-identifier tables (Schema, MLoS, Settlement,
    Takeoffpoint, Boundary) — no more, no fewer — and every one of them must yield at least two
    identifiers. A parser that silently matched zero tables, or matched the Auto Correct table
    too, would make the comparison in the next test vacuous or permanently wrong."""
    source = APP_PY_PATH.read_text()
    tables = parse_reference_tables(source)
    assert len(tables) == 5, (
        f"expected exactly 5 'Rule'/'Check' reference tables in app.py, found {len(tables)}: {tables}"
    )
    for i, ids in enumerate(tables):
        assert len(ids) >= 2, f"reference table #{i} yielded fewer than 2 identifiers: {ids}"


def test_reference_tables_and_registry_list_the_same_identifiers():
    """The union of identifiers across all five reference tables must equal the set returned by
    ``qc.canonical_order()`` exactly — no identifier documented that the engine does not emit,
    and none emitted that the reference does not document. The two set differences are reported
    separately, since each is a distinct failure of trust for an officer reading the sidebar."""
    source = APP_PY_PATH.read_text()
    tables = parse_reference_tables(source)

    reference_ids: set = set()
    for ids in tables:
        reference_ids.update(ids)

    registry_ids = set(qc.canonical_order())

    documented_but_not_emitted = sorted(reference_ids - registry_ids)
    emitted_but_not_documented = sorted(registry_ids - reference_ids)

    assert not documented_but_not_emitted and not emitted_but_not_documented, (
        "the sidebar rules reference and the registry disagree:\n"
        f"  documented in the reference but not emitted by the engine: {documented_but_not_emitted}\n"
        f"  emitted by the engine but not documented in the reference: {emitted_but_not_documented}"
    )
