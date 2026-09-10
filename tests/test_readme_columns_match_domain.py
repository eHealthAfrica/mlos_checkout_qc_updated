"""Structural backstop for D-20: README.md is the canonical column vocabulary, and a
future divergence between its two required-columns tables and qc/domain.py's
MLOS_REQUIRED_COLS / TAKEOFF_REQUIRED_COLS must be treated as a defect. Verified during
planning to match exactly, with zero drift, at the time of this discussion — nothing
before this file asserted that equality standingly, so the directive rested on
discipline alone. This test gives it a standing structural check, in the shape
tests/test_rules_reference_matches_registry.py already established for a sibling
sidebar/registry agreement problem.
"""

import re
from pathlib import Path

from qc.domain import MLOS_REQUIRED_COLS, TAKEOFF_REQUIRED_COLS

README_PATH = Path(__file__).resolve().parent.parent / "README.md"

_MLOS_HEADING_RE = re.compile(r"^####\s*Required MLoS Columns \(43\)\s*$")
_TAKEOFF_HEADING_RE = re.compile(r"^####\s*Required Takeoffpoint Columns \(4\)\s*$")
_FIRST_BACKTICK_CELL_RE = re.compile(r"^\|\s*`([^`]+)`")


def _parse_columns_under_heading(source: str, heading_re: "re.Pattern") -> "list[str]":
    """Return the column names read from the first backticked cell of every table row
    following the given heading — skipping the blank line, the header row and the
    separator row — stopping at the first line that is not itself a pipe-delimited
    table row (a blank line or trailing prose). Mirrors
    tests/test_rules_reference_matches_registry.py's parser shape."""
    lines = source.splitlines()
    names: "list[str]" = []
    for i, line in enumerate(lines):
        if not heading_re.match(line.strip()):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("|"):
            j += 1
        j += 2  # skip the header row and its separator row
        while j < len(lines):
            stripped = lines[j].strip()
            if not stripped.startswith("|"):
                break
            match = _FIRST_BACKTICK_CELL_RE.match(stripped)
            if match:
                names.append(match.group(1))
            j += 1
        break
    return names


def test_readme_mlos_columns_match_domain():
    """The set of column names under README.md's 'Required MLoS Columns (43)' heading
    must equal qc.domain.MLOS_REQUIRED_COLS exactly — a column documented but not
    required, and a column required but not documented, are reported separately, since
    each is a distinct failure of D-20's canonical-vocabulary directive."""
    source = README_PATH.read_text()
    readme_names = set(_parse_columns_under_heading(source, _MLOS_HEADING_RE))

    documented_but_not_required = sorted(readme_names - MLOS_REQUIRED_COLS)
    required_but_not_documented = sorted(MLOS_REQUIRED_COLS - readme_names)

    assert not documented_but_not_required and not required_but_not_documented, (
        "README.md's Required MLoS Columns table and qc.domain.MLOS_REQUIRED_COLS disagree:\n"
        f"  documented but not required: {documented_but_not_required}\n"
        f"  required but not documented: {required_but_not_documented}"
    )


def test_readme_takeoff_columns_match_domain():
    """The set of column names under README.md's 'Required Takeoffpoint Columns (4)'
    heading must equal qc.domain.TAKEOFF_REQUIRED_COLS exactly."""
    source = README_PATH.read_text()
    readme_names = set(_parse_columns_under_heading(source, _TAKEOFF_HEADING_RE))

    documented_but_not_required = sorted(readme_names - TAKEOFF_REQUIRED_COLS)
    required_but_not_documented = sorted(TAKEOFF_REQUIRED_COLS - readme_names)

    assert not documented_but_not_required and not required_but_not_documented, (
        "README.md's Required Takeoffpoint Columns table and qc.domain.TAKEOFF_REQUIRED_COLS "
        f"disagree:\n  documented but not required: {documented_but_not_required}\n"
        f"  required but not documented: {required_but_not_documented}"
    )


def test_readme_parser_found_the_expected_counts():
    """Defensive floor: the parser must find exactly 43 and 4 names respectively, so
    this suite cannot green because a heading was renamed and the parser silently
    matched nothing — the two equality tests above would be vacuously true against an
    empty parsed set otherwise."""
    source = README_PATH.read_text()
    mlos_names = _parse_columns_under_heading(source, _MLOS_HEADING_RE)
    takeoff_names = _parse_columns_under_heading(source, _TAKEOFF_HEADING_RE)

    assert len(mlos_names) == 43, (
        f"expected 43 MLoS column names, parser found {len(mlos_names)}: {mlos_names}"
    )
    assert len(takeoff_names) == 4, (
        f"expected 4 Takeoffpoint column names, parser found {len(takeoff_names)}: {takeoff_names}"
    )
